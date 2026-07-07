"""Utilidades compartidas para redactores LLM opcionales de reportes."""

from __future__ import annotations

import json
from typing import Any, Mapping

from puce_mocap.report_interpreter import ReportInterpretation


SENSITIVE_FIELDS = {
    "session_id",
    "codigo_paciente",
    "nombre_paciente",
    "lesion",
    "observaciones_paciente",
    "observacion",
    "institucion",
    "programa",
    "contraparte",
    "estudiante",
    "carrera",
    "tutor",
    "proyecto_base",
    "licencia",
    "aviso_no_diagnostico",
}
MAX_ITEMS = 5


def build_prompt(kind: str, rows: list[dict[str, str]], deterministic: ReportInterpretation) -> str:
    """Construye un prompt sin identificadores personales ni observaciones libres."""
    metrics = [_sanitize_row(row) for row in rows]
    source = {
        "tipo_reporte": kind,
        "metricas_anonimizadas": metrics,
        "interpretacion_base": {
            "resumen": deterministic.resumen,
            "hallazgos": deterministic.hallazgos[:MAX_ITEMS],
            "recomendaciones": deterministic.recomendaciones[:MAX_ITEMS],
            "limitaciones": deterministic.limitaciones[:MAX_ITEMS],
        },
    }
    return (
        "Redacta una interpretacion breve en espanol para un reporte de fisioterapia comunitaria. "
        "Usa solo los datos anonimizados y la interpretacion base. No agregues datos nuevos, no diagnostiques, "
        "no uses lenguaje alarmista y no menciones nombres, codigos, lesiones ni observaciones libres. "
        "Responde exclusivamente JSON valido con las claves resumen, hallazgos, recomendaciones y limitaciones. "
        "hallazgos, recomendaciones y limitaciones deben ser listas cortas de texto.\n\n"
        f"Datos:\n{json.dumps(source, ensure_ascii=False)}"
    )


def parse_interpretation_json(text: str, provider: str) -> ReportInterpretation:
    """Convierte una respuesta JSON estricta en ReportInterpretation."""
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("La respuesta del modelo no es un objeto JSON.")
    summary = _required_text(parsed.get("resumen"))
    findings = _text_list(parsed.get("hallazgos"))
    recommendations = _text_list(parsed.get("recomendaciones"))
    limitations = _text_list(parsed.get("limitaciones"))
    if not findings or not recommendations or not limitations:
        raise ValueError("La respuesta del modelo no contiene secciones completas.")
    return ReportInterpretation(
        provider=provider,
        resumen=summary,
        hallazgos=findings[:MAX_ITEMS],
        recomendaciones=recommendations[:MAX_ITEMS],
        limitaciones=limitations[:MAX_ITEMS],
    )


def _sanitize_row(row: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in row.items()
        if key not in SENSITIVE_FIELDS and value not in (None, "")
    }


def _required_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Texto requerido vacio.")
    return text


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result
