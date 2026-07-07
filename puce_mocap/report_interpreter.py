"""Interpretacion local y segura para reportes de sesion."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from typing import Mapping


PROHIBITED_TERMS = (
    "diagnóstico",
    "diagnostico",
    "lesión detectada",
    "lesion detectada",
    "enfermedad detectada",
    "riesgo grave",
)


@dataclass(frozen=True)
class ReportInterpretation:
    """Texto resumido para una seccion humana del PDF."""

    provider: str
    resumen: str
    hallazgos: list[str]
    recomendaciones: list[str]
    limitaciones: list[str]


def build_report_interpretation(kind: str, rows: list[dict[str, str]]) -> ReportInterpretation:
    """Genera interpretacion deterministica y, opcionalmente, redaccion con un LLM configurado."""
    deterministic = build_deterministic_interpretation(kind, rows)
    mode = os.environ.get("PUCE_MOCAP_REPORT_INTERPRETER", "deterministic").strip().lower()
    if mode in {"openrouter", "openrouter_remoto"}:
        try:
            from puce_mocap.openrouter_interpreter import build_openrouter_interpretation

            return build_openrouter_interpretation(kind, rows, deterministic)
        except Exception:
            return deterministic

    if mode not in {"lfm_ollama", "lfm", "ollama"}:
        return deterministic

    try:
        from puce_mocap.local_lfm_interpreter import build_lfm_interpretation

        return build_lfm_interpretation(kind, rows, deterministic)
    except Exception:
        return deterministic


def build_deterministic_interpretation(kind: str, rows: list[dict[str, str]]) -> ReportInterpretation:
    """Construye interpretacion local usando solo reglas reproducibles."""
    if not rows:
        return _clean(
            ReportInterpretation(
                provider="deterministico_local",
                resumen="No hay datos suficientes para interpretar la sesion.",
                hallazgos=["El reporte no contiene registros evaluables."],
                recomendaciones=["Repetir la sesion con articulaciones visibles antes de revisar resultados."],
                limitaciones=_base_limitations(),
            )
        )
    if kind == "pesas":
        return _clean(_interpret_weights(rows))
    if kind == "rehabilitacion":
        return _clean(_interpret_rehab(rows))
    if kind == "marcha":
        return _clean(_interpret_gait(rows))
    return _clean(
        ReportInterpretation(
            provider="deterministico_local",
            resumen="Reporte generado con metricas de sesion disponibles.",
            hallazgos=["El tipo de reporte no tiene reglas especificas de interpretacion."],
            recomendaciones=["Revisar las metricas con el fisioterapeuta responsable."],
            limitaciones=_base_limitations(),
        )
    )


def interpretation_has_prohibited_terms(interpretation: ReportInterpretation) -> bool:
    text = " ".join(
        [
            interpretation.resumen,
            *interpretation.hallazgos,
            *interpretation.recomendaciones,
            *interpretation.limitaciones,
        ]
    ).lower()
    return any(term in text for term in PROHIBITED_TERMS)


def _interpret_weights(rows: list[Mapping[str, str]]) -> ReportInterpretation:
    valid_rows = [row for row in rows if _as_int(row.get("total_frames")) > 0]
    total_reps = sum(_as_int(row.get("repeticiones")) for row in valid_rows)
    evaluable_frames = sum(_as_int(row.get("frames_evaluables_forma")) for row in valid_rows)
    correct_frames = sum(_as_int(row.get("frames_correctos")) for row in valid_rows)
    percent = _percent(correct_frames, evaluable_frames)
    exercises = [_display(row.get("ejercicio")) for row in valid_rows if row.get("ejercicio")]

    resumen = (
        f"La sesion de pesas registro {total_reps} repeticiones en {len(valid_rows)} ejercicio(s) "
        f"con {percent:.1f} % de fotogramas evaluables en postura correcta."
    )
    hallazgos = [
        f"Se analizaron {evaluable_frames} fotogramas evaluables de forma.",
        f"Ejercicios registrados: {', '.join(exercises) if exercises else 'no disponible'}.",
    ]
    if percent >= 85.0:
        hallazgos.append("La mayor parte del tiempo evaluable se mantuvo dentro de la tecnica esperada.")
    elif percent >= 60.0:
        hallazgos.append("La sesion alterno fotogramas correctos con momentos que requieren ajuste tecnico.")
    else:
        hallazgos.append("Predominaron fotogramas que requieren correccion de postura o mejor encuadre.")

    messages = _unique_observations(valid_rows)
    if messages:
        hallazgos.append(f"Observaciones principales del sistema: {'; '.join(messages[:3])}.")

    recomendaciones = [
        "Revisar los segmentos con menor porcentaje correcto antes de aumentar carga o velocidad.",
    ]
    if percent < 85.0:
        recomendaciones.append("Priorizar una ejecucion lenta y supervisada hasta estabilizar la postura.")
    if evaluable_frames == 0:
        recomendaciones.append("Mejorar encuadre e iluminacion para obtener fotogramas evaluables.")

    return ReportInterpretation(
        provider="deterministico_local",
        resumen=resumen,
        hallazgos=hallazgos,
        recomendaciones=recomendaciones,
        limitaciones=_base_limitations(),
    )


def _interpret_rehab(rows: list[Mapping[str, str]]) -> ReportInterpretation:
    valid_rows = [
        row
        for row in rows
        if any(
            str(row.get(field, "")).strip()
            for field in (
                "porcentaje_dentro_rango",
                "repeticiones_realizadas",
                "angulo_maximo_alcanzado",
                "comparacion_sesion_anterior",
            )
        )
    ]
    if not valid_rows:
        return ReportInterpretation(
            provider="deterministico_local",
            resumen="La sesion de rehabilitacion no tiene fotogramas validos suficientes.",
            hallazgos=["No se detectaron articulaciones suficientes para estimar el desempeno del ejercicio."],
            recomendaciones=["Repetir la captura manteniendo visibles las articulaciones requeridas."],
            limitaciones=_base_limitations(),
        )

    total_reps = sum(_as_int(row.get("repeticiones_realizadas")) for row in valid_rows)
    target_reps = sum(_as_int(row.get("repeticiones_objetivo")) for row in valid_rows)
    weighted_percent = _average(valid_rows, "porcentaje_dentro_rango")
    reached_angles = [_as_float(row.get("angulo_maximo_alcanzado")) for row in valid_rows]
    reached_angles = [angle for angle in reached_angles if angle is not None]

    resumen = (
        f"La sesion de rehabilitacion registro {total_reps} de {target_reps} repeticion(es) objetivo "
        f"y {weighted_percent:.1f} % del tiempo valido dentro del rango configurado."
    )
    hallazgos = [
        f"Se resumieron {len(valid_rows)} ejercicio(s) con metricas de rango o repeticion.",
    ]
    if reached_angles:
        hallazgos.append(f"El angulo maximo alcanzado observado fue {max(reached_angles):.1f} grados.")
    comparison = _first_non_empty(row.get("comparacion_sesion_anterior") for row in valid_rows)
    if comparison:
        hallazgos.append(f"Comparacion tecnica: {comparison}")
    if weighted_percent >= 75.0:
        hallazgos.append(
            "El ejercicio permanecio la mayor parte del tiempo valido dentro del rango terapeutico configurado."
        )
    elif weighted_percent >= 40.0:
        hallazgos.append("El ejercicio tuvo ingreso parcial al rango configurado durante la sesion.")
    else:
        hallazgos.append("El ejercicio estuvo la mayor parte del tiempo valido fuera del rango configurado.")

    recomendaciones = ["Usar estos resultados como apoyo para ajustar rango, lado o repeticiones bajo supervision."]
    if total_reps < target_reps:
        recomendaciones.append(
            "Revisar si el objetivo de repeticiones es adecuado para la siguiente sesion supervisada."
        )
    if weighted_percent < 75.0:
        recomendaciones.append("Confirmar encuadre y ritmo del movimiento antes de interpretar cambios entre sesiones.")

    return ReportInterpretation(
        provider="deterministico_local",
        resumen=resumen,
        hallazgos=hallazgos,
        recomendaciones=recomendaciones,
        limitaciones=_base_limitations(),
    )


def _interpret_gait(rows: list[Mapping[str, str]]) -> ReportInterpretation:
    row = rows[-1]
    frames_valid = _as_int(row.get("frames_validos"))
    green = _as_float(row.get("porcentaje_verde")) or 0.0
    yellow = _as_float(row.get("porcentaje_amarillo")) or 0.0
    red = _as_float(row.get("porcentaje_rojo")) or 0.0
    state = _display(row.get("estado_global"))

    resumen = (
        f"La sesion de marcha tuvo estado general {state} con {frames_valid} fotogramas validos "
        f"({green:.1f} % normal, {yellow:.1f} % atencion, {red:.1f} % revisar)."
    )
    hallazgos = [
        f"Inclinacion media del tronco: {_format_metric(row.get('promedio_inclinacion_tronco'), 'grados')}.",
        f"Asimetria media entre rodillas: {_format_metric(row.get('promedio_asimetria_rodillas'), 'grados')}.",
        f"Longitud media de paso: {_format_metric(row.get('promedio_longitud_paso'), 'unidades de la fuente')}.",
    ]
    if red >= 20.0:
        hallazgos.append("Una proporcion relevante de la sesion quedo marcada para revisar con fisioterapeuta.")
    elif yellow + red >= 20.0:
        hallazgos.append("La sesion presento momentos de atencion tecnica que conviene revisar.")
    else:
        hallazgos.append("La mayor parte de la sesion se mantuvo en el estado normal definido por el sistema.")

    recomendaciones = ["Revisar los resultados junto con la observacion directa de la caminata."]
    asymmetry = _as_float(row.get("promedio_asimetria_rodillas"))
    if asymmetry is not None and asymmetry > 10.0:
        recomendaciones.append("Verificar simetria de rodillas en una nueva toma supervisada.")
    trunk = _as_float(row.get("promedio_inclinacion_tronco"))
    if trunk is not None and trunk > 15.0:
        recomendaciones.append("Revisar postura de tronco y ubicacion de la camara antes de repetir la prueba.")

    return ReportInterpretation(
        provider="deterministico_local",
        resumen=resumen,
        hallazgos=hallazgos,
        recomendaciones=recomendaciones,
        limitaciones=_base_limitations(),
    )


def _clean(interpretation: ReportInterpretation) -> ReportInterpretation:
    if interpretation_has_prohibited_terms(interpretation):
        return replace(
            interpretation,
            provider="deterministico_local",
            resumen="Interpretacion automatica omitida por seguridad del lenguaje.",
            hallazgos=["Revise las metricas del reporte con el fisioterapeuta responsable."],
            recomendaciones=["Evitar conclusiones clinicas automaticas a partir de esta herramienta."],
            limitaciones=_base_limitations(),
        )
    return interpretation


def _base_limitations() -> list[str]:
    return [
        "La interpretacion es automatica y se basa solo en metricas calculadas por el sistema.",
        "No reemplaza la evaluacion de un fisioterapeuta ni emite conclusiones clinicas.",
    ]


def _as_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: object) -> int:
    number = _as_float(value)
    if number is None:
        return 0
    return int(round(number))


def _percent(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return (part / total) * 100.0


def _average(rows: list[Mapping[str, str]], value_field: str) -> float:
    values = []
    for row in rows:
        value = _as_float(row.get(value_field))
        if value is not None:
            values.append(value)
    if not values:
        return 0.0
    return sum(values) / len(values)


def _unique_observations(rows: list[Mapping[str, str]]) -> list[str]:
    observations: list[str] = []
    for row in rows:
        raw = str(row.get("observacion", "") or "")
        for part in raw.replace(".; ", ". ").split(" | "):
            text = part.strip(" ;.")
            if text and text not in observations:
                observations.append(text)
    return observations


def _first_non_empty(values) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _display(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "no disponible"
    labels = {
        "NORMAL": "normal",
        "ATENCION": "atencion",
        "REVISAR_CON_FISIOTERAPEUTA": "revisar con fisioterapeuta",
    }
    return labels.get(text, text.replace("_", " ").lower())


def _format_metric(value: object, unit: str) -> str:
    number = _as_float(value)
    if number is None:
        return "no disponible"
    return f"{number:.1f} {unit}"
