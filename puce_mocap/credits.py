"""Créditos institucionales y licencia compartidos por las interfaces PUCE."""

from __future__ import annotations

from pathlib import Path
from typing import Any


STUDENTS = (
    "Jossue Hermel Gallardo Toro",
    "Kevin Lima Blanco",
)
TUTOR = "Francisco Rodríguez Clavijo"
PROJECT_DESCRIPTION = (
    "Proyecto de Vinculación con la Comunidad de la Dirección de Vinculación "
    "con la Colectividad de la Pontificia Universidad Católica del Ecuador, "
    "desarrollado en la Carrera de Ingeniería en Sistemas de Información durante el año 2026."
)
FREEMOCAP_NAME = "FreeMoCap — Free Motion Capture for Everyone"
FREEMOCAP_REPOSITORY = "https://github.com/freemocap/freemocap"
FREEMOCAP_WEBSITE = "https://freemocap.org"
LICENSE_NAME = "GNU Affero General Public License, versión 3 (AGPLv3)"


def license_path() -> Path:
    """Devuelve la licencia AGPLv3 original conservada en la raíz del proyecto."""
    return Path(__file__).resolve().parents[1] / "LICENSE"


def license_text() -> str:
    """Lee sin modificaciones el texto completo de la licencia del proyecto."""
    return license_path().read_text(encoding="utf-8")


def credits_payload() -> dict[str, Any]:
    """Construye los créditos completos para clientes de la aplicación."""
    return {
        "students": list(STUDENTS),
        "tutor": TUTOR,
        "project_description": PROJECT_DESCRIPTION,
        "original_project": {
            "name": FREEMOCAP_NAME,
            "repository": FREEMOCAP_REPOSITORY,
            "website": FREEMOCAP_WEBSITE,
        },
        "license_name": LICENSE_NAME,
        "license_text": license_text(),
    }
