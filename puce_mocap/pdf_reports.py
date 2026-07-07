"""Reportes PDF legibles para las sesiones registradas en CSV."""

from __future__ import annotations

import csv
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from puce_mocap.credits import SOURCE_CODE_REPOSITORY, STUDENTS, TUTOR
from puce_mocap.report_interpreter import ReportInterpretation, build_report_interpretation
from puce_mocap.reports_v2 import INSTITUTIONAL
from puce_mocap.resources import resource_file


REPORT_CONFIG = {
    "pesas": {
        "title": "Reporte de ejercicios con pesas",
        "prefix": "pesas",
        "fields": [
            "ejercicio", "fecha", "fuente_datos", "angulo_minimo_inicio", "angulo_maximo_inicio",
            "angulo_minimo_objetivo", "angulo_maximo_objetivo", "total_frames", "frames_evaluables_forma",
            "frames_correctos", "porcentaje_correcto", "repeticiones",
        ],
    },
    "rehabilitacion": {
        "title": "Reporte de rehabilitación fisioterapéutica",
        "prefix": "rehabilitacion",
        "fields": [
            "ejercicio", "lado", "fecha", "fuente_datos", "angulo_minimo_inicio", "angulo_maximo_inicio",
            "angulo_minimo_objetivo", "angulo_maximo_objetivo", "angulo_maximo_alcanzado",
            "repeticiones_objetivo", "repeticiones_realizadas", "porcentaje_dentro_rango",
            "comparacion_sesion_anterior",
        ],
    },
    "marcha": {
        "title": "Reporte de análisis de marcha",
        "prefix": "marcha",
        "fields": [
            "fecha", "fuente_datos", "duracion_segundos", "total_frames", "frames_validos",
            "porcentaje_verde", "porcentaje_amarillo", "porcentaje_rojo", "promedio_inclinacion_tronco",
            "promedio_asimetria_rodillas", "promedio_longitud_paso", "estado_global",
        ],
    },
}

FIELD_LABELS = {
    "session_id": "Identificador de sesión",
    "fecha": "Fecha y hora",
    "fuente_datos": "Fuente de datos",
    "codigo_paciente": "Código del paciente",
    "nombre_paciente": "Paciente",
    "lesion": "Condición / lesión",
    "observaciones_paciente": "Observaciones del paciente",
    "ejercicio": "Ejercicio",
    "lado": "Extremidad evaluada",
    "angulo_minimo_inicio": "Ángulo inicial mínimo",
    "angulo_maximo_inicio": "Ángulo inicial máximo",
    "angulo_minimo_objetivo": "Ángulo objetivo mínimo",
    "angulo_maximo_objetivo": "Ángulo objetivo máximo",
    "angulo_maximo_alcanzado": "Ángulo máximo alcanzado",
    "total_frames": "Fotogramas totales",
    "frames_validos": "Fotogramas válidos",
    "frames_evaluables_forma": "Fotogramas evaluables",
    "frames_correctos": "Fotogramas con postura correcta",
    "porcentaje_correcto": "Tiempo con postura correcta",
    "repeticiones": "Repeticiones",
    "repeticiones_objetivo": "Repeticiones objetivo",
    "repeticiones_realizadas": "Repeticiones realizadas",
    "porcentaje_dentro_rango": "Tiempo dentro del rango",
    "comparacion_sesion_anterior": "Comparación con sesión anterior",
    "duracion_segundos": "Duración",
    "porcentaje_verde": "Estado normal",
    "porcentaje_amarillo": "Estado de atención",
    "porcentaje_rojo": "Estado para revisión",
    "promedio_inclinacion_tronco": "Inclinación media del tronco",
    "promedio_asimetria_rodillas": "Asimetría media entre rodillas",
    "promedio_longitud_paso": "Longitud media de paso",
    "estado_global": "Estado general",
    "observacion": "Observaciones de la sesión",
}

PERCENT_FIELDS = {
    "porcentaje_correcto",
    "porcentaje_dentro_rango",
    "porcentaje_verde",
    "porcentaje_amarillo",
    "porcentaje_rojo",
}
ANGLE_FIELDS = {
    "angulo_minimo_inicio",
    "angulo_maximo_inicio",
    "angulo_minimo_objetivo",
    "angulo_maximo_objetivo",
    "angulo_maximo_alcanzado",
    "promedio_inclinacion_tronco",
    "promedio_asimetria_rodillas",
}
VALUE_LABELS = {
    "flexion_codo": "Flexión de codo",
    "abduccion_hombro": "Abducción de hombro",
    "rotacion_muneca": "Rotación de muñeca",
    "extension_rodilla": "Extensión de rodilla",
    "dorsiflexion_tobillo": "Dorsiflexión de tobillo",
    "elevacion_pierna_recta": "Elevación de pierna recta",
    "auto": "Automática",
    "left": "Izquierda",
    "right": "Derecha",
    "NORMAL": "Normal",
    "ATENCION": "Atención",
    "REVISAR_CON_FISIOTERAPEUTA": "Revisar con fisioterapeuta",
    "freemocap_session": "Sesión FreeMoCap",
    "mediapipe_live": "Cámara en vivo",
}


def _report_kind(path: Path) -> str:
    stem = path.stem.lower()
    for kind, config in REPORT_CONFIG.items():
        if stem.startswith(config["prefix"]):
            return kind
    raise ValueError(f"No se reconoce el tipo de reporte CSV: {path.name}")


def _latest_session_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("El reporte CSV no contiene sesiones para exportar a PDF.")
    session_id = rows[-1].get("session_id", "")
    if not session_id:
        return [rows[-1]]
    return [row for row in rows if row.get("session_id") == session_id]


def _display_value(field: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "No disponible"
    if field == "fecha":
        return text.replace("T", " ")
    if field in {"ejercicio", "lado", "estado_global", "fuente_datos"}:
        return VALUE_LABELS.get(text, text.replace("_", " ").capitalize())
    if field in PERCENT_FIELDS:
        return f"{text} %"
    if field in ANGLE_FIELDS:
        return f"{text} grados"
    if field == "duracion_segundos":
        return f"{text} segundos"
    return text.replace(" | ", "; ").replace(".; ", ". ")


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)


def _provider_label(provider: str) -> str:
    labels = {
        "deterministico_local": "Reglas determinísticas locales",
        "lfm_ollama_local": "LFM local vía Ollama",
        "openrouter_remoto": "Modelo remoto vía OpenRouter",
    }
    return labels.get(provider, provider.replace("_", " "))


def _interpretation_story(
    interpretation: ReportInterpretation,
    heading_style: ParagraphStyle,
    body_style: ParagraphStyle,
    small_style: ParagraphStyle,
) -> list:
    story = [
        Paragraph("Interpretación automática local", heading_style),
        Paragraph(f"Proveedor usado: {escape(_provider_label(interpretation.provider))}", small_style),
        _paragraph(interpretation.resumen, body_style),
    ]
    sections = [
        ("Hallazgos", interpretation.hallazgos),
        ("Recomendaciones", interpretation.recomendaciones),
        ("Limitaciones", interpretation.limitaciones),
    ]
    for title, items in sections:
        if not items:
            continue
        story.append(Paragraph(title, small_style))
        for item in items:
            story.append(_paragraph(f"- {item}", body_style))
    story.append(Spacer(1, 3 * mm))
    return story


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B8C9C4"))
    canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
    canvas.setFillColor(colors.HexColor("#526963"))
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(18 * mm, 9 * mm, "Herramienta de apoyo; no sustituye la evaluación de un fisioterapeuta.")
    canvas.drawRightString(192 * mm, 9 * mm, f"Página {document.page}")
    canvas.restoreState()


def export_pdf_report(csv_path: str | Path, path: str | Path | None = None) -> Path:
    """Genera un PDF humano-legible con la sesión más reciente del CSV indicado."""
    source = Path(csv_path)
    if not source.is_file():
        raise FileNotFoundError(f"No existe el reporte CSV: {source}")
    kind = _report_kind(source)
    config = REPORT_CONFIG[kind]
    rows = _latest_session_rows(source)
    output = Path(path) if path else source.with_suffix(".pdf")
    output.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19,
        leading=23, textColor=colors.HexColor("#123F38"), alignment=TA_LEFT, spaceAfter=5 * mm,
    )
    eyebrow_style = ParagraphStyle(
        "Eyebrow", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8,
        leading=10, textColor=colors.HexColor("#007A6D"), uppercase=True, spaceAfter=2 * mm,
    )
    heading_style = ParagraphStyle(
        "Heading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12,
        leading=15, textColor=colors.HexColor("#173F39"), spaceBefore=3 * mm, spaceAfter=2.5 * mm,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9,
        leading=13, textColor=colors.HexColor("#263B37"), spaceAfter=2 * mm,
    )
    small_style = ParagraphStyle(
        "Small", parent=body_style, fontSize=7.5, leading=10, textColor=colors.HexColor("#526963"),
    )
    cell_style = ParagraphStyle(
        "Cell", parent=body_style, fontSize=8.5, leading=11, spaceAfter=0,
    )
    cell_label_style = ParagraphStyle(
        "CellLabel", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.HexColor("#294E47"),
    )
    table_header_style = ParagraphStyle(
        "TableHeader", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white,
    )

    document = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=14 * mm, bottomMargin=16 * mm, title=config["title"],
        author="Pontificia Universidad Católica del Ecuador",
    )
    text_header = [
        Paragraph("PUCE MOCAP - VINCULACIÓN CON LA COMUNIDAD - 2026", eyebrow_style),
        Paragraph(config["title"], title_style),
        Paragraph(
            "Pontificia Universidad Católica del Ecuador - Dirección de Vinculación con la Colectividad<br/>"
            "Carrera de Ingeniería en Sistemas de Información - Fe y Alegría Ecuador",
            body_style,
        ),
        Paragraph(
            f"Estudiantes: {escape(' y '.join(STUDENTS))} &nbsp;&nbsp;|&nbsp;&nbsp; Tutor: {escape(TUTOR)}",
            small_style,
        ),
        Paragraph(
            f'Código fuente: <link href="{SOURCE_CODE_REPOSITORY}" color="#006E62">'
            f"{SOURCE_CODE_REPOSITORY}</link>",
            small_style,
        ),
    ]

    logo_path = resource_file("assets", "logo_puce.png")
    if logo_path.is_file():
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(str(logo_path))
        iw, ih = img_reader.getSize()
        aspect = ih / float(iw)
        
        img_width = 40 * mm
        img_height = img_width * aspect
        logo_img = Image(str(logo_path), width=img_width, height=img_height)
        
        header_table = Table(
            [[text_header, logo_img]], 
            colWidths=[130 * mm, 44 * mm],
            hAlign="LEFT"
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story = [header_table, Spacer(1, 3 * mm)]
    else:
        story = text_header + [Spacer(1, 3 * mm)]

    first = rows[0]
    patient_fields = [
        ("Código del paciente", first.get("codigo_paciente")),
        ("Paciente", first.get("nombre_paciente")),
        ("Condición / lesión", first.get("lesion")),
        ("Observaciones", first.get("observaciones_paciente")),
    ]
    if any(value for _label, value in patient_fields):
        patient_data = [
            [_paragraph(label, cell_label_style), _paragraph(_display_value("", value), cell_style)]
            for label, value in patient_fields
        ]
        patient_table = Table(patient_data, colWidths=[48 * mm, 126 * mm], hAlign="LEFT")
        patient_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F1EE")),
            ("BACKGROUND", (1, 0), (1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C9C4")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([Paragraph("Datos de la sesión", heading_style), patient_table, Spacer(1, 4 * mm)])

    interpretation = build_report_interpretation(kind, rows)
    story.extend(_interpretation_story(interpretation, heading_style, body_style, small_style))

    for index, row in enumerate(rows, start=1):
        section_name = row.get("ejercicio") or f"Registro {index}"
        metric_data = [[_paragraph("Métrica", table_header_style), _paragraph("Resultado", table_header_style)]]
        for field in config["fields"]:
            metric_data.append([
                _paragraph(FIELD_LABELS.get(field, field.replace("_", " ").capitalize()), cell_label_style),
                _paragraph(_display_value(field, row.get(field)), cell_style),
            ])
        metrics = Table(metric_data, colWidths=[70 * mm, 104 * mm], repeatRows=1, hAlign="LEFT")
        metrics.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D6E63")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6F5")]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C9C4")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.extend([
            KeepTogether([
                Paragraph(f"{index}. {escape(section_name)}", heading_style),
                Paragraph(f"Sesión: {escape(row.get('session_id', 'No disponible'))}", small_style),
            ]),
            metrics,
        ])
        observation = _display_value("observacion", row.get("observacion"))
        if observation != "No disponible":
            story.extend([
                Paragraph("Observaciones", heading_style),
                _paragraph(observation, body_style),
            ])
        story.append(Spacer(1, 4 * mm))

    story.extend([
        Paragraph("Aviso importante", heading_style),
        Paragraph(INSTITUTIONAL["aviso_no_diagnostico"], body_style),
        Paragraph(
            "Los resultados deben interpretarse bajo supervisión profesional. "
            "El sistema no emite diagnósticos médicos.",
            body_style,
        ),
    ])
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output
