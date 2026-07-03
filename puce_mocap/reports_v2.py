"""Reportes CSV acumulativos, institucionales y resistentes a fórmulas."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping, Any

from puce_mocap.app_paths import reports_dir


INSTITUTIONAL = {
    "institucion": "Pontificia Universidad Católica del Ecuador",
    "programa": "Vinculación con la Comunidad",
    "contraparte": "Fe y Alegría Ecuador",
    "anio": "2026",
    "estudiante": "Jossue Hermel Gallardo Toro; Kevin Lima Blanco",
    "carrera": "Ingeniería en Sistemas de Información",
    "tutor": "Francisco Rodríguez Clavijo",
    "proyecto_base": "FreeMoCap - Free Motion Capture for Everyone",
    "licencia": "AGPLv3",
    "aviso_no_diagnostico": "Herramienta de apoyo; no sustituye la evaluación de un fisioterapeuta.",
}
INSTITUTIONAL_FIELDS = list(INSTITUTIONAL)


def sanitize_csv_value(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    if isinstance(value, (list, tuple)):
        value = " | ".join(str(item) for item in value)
    return value


def _rows_with_current_schema(path: Path, fields: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    """Lee CSV históricos y recupera filas escritas con una cabecera anterior."""
    with path.open(newline="", encoding="utf-8") as stream:
        raw_rows = list(csv.reader(stream))
    if not raw_rows:
        return [], []
    header = raw_rows[0]
    rows = []
    for values in raw_rows[1:]:
        # Una fila nueva pudo haberse añadido debajo de una cabecera antigua.
        # Su cantidad de valores permite reconstruirla con el esquema actual.
        schema = fields if len(values) == len(fields) else header
        rows.append(dict(zip(schema, values)))
    return header, rows


def _ensure_csv_schema(path: Path, fields: list[str]) -> None:
    """Migra de forma atómica un CSV acumulativo cuando cambian sus columnas."""
    if not path.exists() or path.stat().st_size == 0:
        return
    header, rows = _rows_with_current_schema(path, fields)
    if header == fields:
        return
    temporary = path.with_name(f".{path.name}.migrating")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fields})
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _append_rows(path: Path, fields: list[str], rows: Iterable[Mapping[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_csv_schema(path, fields)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for row in rows:
            complete = {**INSTITUTIONAL, **row}
            writer.writerow({field: sanitize_csv_value(complete.get(field, "")) for field in fields})
    return path


WEIGHTS_FIELDS = INSTITUTIONAL_FIELDS + [
    "session_id", "fecha", "fuente_datos", "codigo_paciente", "nombre_paciente", "lesion",
    "observaciones_paciente", "ejercicio", "angulo_minimo_inicio", "angulo_maximo_inicio",
    "angulo_minimo_objetivo", "angulo_maximo_objetivo", "total_frames", "frames_evaluables_forma",
    "frames_correctos", "porcentaje_correcto", "repeticiones", "observacion",
]
REHAB_FIELDS = INSTITUTIONAL_FIELDS + [
    "session_id", "fecha", "fuente_datos", "codigo_paciente", "nombre_paciente", "lesion",
    "observaciones_paciente", "ejercicio", "lado", "angulo_minimo_inicio", "angulo_maximo_inicio",
    "angulo_minimo_objetivo", "angulo_maximo_objetivo", "angulo_maximo_alcanzado",
    "repeticiones_objetivo", "repeticiones_realizadas", "porcentaje_dentro_rango",
    "comparacion_sesion_anterior", "observacion",
]
GAIT_FIELDS = INSTITUTIONAL_FIELDS + [
    "session_id", "fecha", "fuente_datos", "duracion_segundos", "total_frames", "frames_validos",
    "porcentaje_verde", "porcentaje_amarillo", "porcentaje_rojo", "promedio_inclinacion_tronco",
    "promedio_asimetria_rodillas", "promedio_longitud_paso", "estado_global", "observacion",
]


def export_weight_sessions(summaries: Iterable[Mapping[str, Any]], path: str | Path | None = None) -> Path:
    rows = []
    for summary in summaries:
        if int(summary.get("total_frames", 0)) == 0:
            continue
        rows.append({**summary, "observacion": summary.get("mensajes_principales", [])})
    return _append_rows(Path(path) if path else reports_dir() / "pesas_v2.csv", WEIGHTS_FIELDS, rows)


def _previous_rehab_row(path: Path, code: str, exercise: str) -> dict[str, str] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    _ensure_csv_schema(path, REHAB_FIELDS)
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    return next(
        (row for row in reversed(rows) if row.get("codigo_paciente") == code and row.get("ejercicio") == exercise),
        None,
    )


def export_rehab_sessions(
    summaries: Iterable[Mapping[str, Any]],
    profile: Mapping[str, Any],
    path: str | Path | None = None,
) -> Path:
    output = Path(path) if path else reports_dir() / "rehabilitacion_v3.csv"
    rows = []
    for summary in summaries:
        if int(summary.get("frames_validos", 0)) == 0:
            continue
        exercise = str(summary.get("ejercicio", ""))
        code = str(summary.get("codigo_paciente", profile.get("codigo_paciente", "")))
        previous = _previous_rehab_row(output, code, exercise)
        comparison = "Sin sesión anterior comparable."
        current_angle = summary.get("angulo_maximo_alcanzado")
        if previous and current_angle is not None:
            try:
                difference = float(current_angle) - float(previous["angulo_maximo_alcanzado"])
                comparison = f"Cambio de {difference:+.2f} grados respecto a la sesión anterior comparable."
            except (ValueError, TypeError, KeyError):
                pass
        rows.append(
            {
                **summary,
                "nombre_paciente": profile.get("nombre", ""),
                "lesion": profile.get("lesion", ""),
                "observaciones_paciente": profile.get("observaciones", ""),
                "repeticiones_realizadas": summary.get("repeticiones_estimadas", 0),
                "comparacion_sesion_anterior": comparison,
                "observacion": summary.get("observaciones", []),
            }
        )
    return _append_rows(output, REHAB_FIELDS, rows)


def export_gait_session(summary: Mapping[str, Any], path: str | Path | None = None) -> Path:
    row = {**summary, "observacion": summary.get("observaciones", [])}
    return _append_rows(Path(path) if path else reports_dir() / "marcha_v2.csv", GAIT_FIELDS, [row])
