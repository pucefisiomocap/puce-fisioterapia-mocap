"""Adaptador opcional para redactar reportes con modelos remotos via OpenRouter."""

from __future__ import annotations

import json
import os
from urllib import request

from puce_mocap.report_interpreter import (
    ReportInterpretation,
    interpretation_has_prohibited_terms,
)
from puce_mocap.report_llm_common import build_prompt, parse_interpretation_json


DEFAULT_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "openrouter/free"
TIMEOUT_SECONDS = 12


def build_openrouter_interpretation(
    kind: str,
    rows: list[dict[str, str]],
    deterministic: ReportInterpretation,
) -> ReportInterpretation:
    """Pide redaccion a OpenRouter y vuelve al texto local si algo falla."""
    api_key = os.environ.get("PUCE_MOCAP_OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError("PUCE_MOCAP_OPENROUTER_API_KEY no esta configurada.")

    payload = {
        "model": os.environ.get("PUCE_MOCAP_OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un asistente de redaccion para reportes de fisioterapia comunitaria. "
                    "No diagnostiques ni agregues informacion fuera de los datos anonimizados."
                ),
            },
            {
                "role": "user",
                "content": build_prompt(kind, rows, deterministic),
            },
        ],
        "temperature": 0.1,
        "top_p": 0.7,
        "max_tokens": 280,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    referer = os.environ.get("PUCE_MOCAP_OPENROUTER_REFERER", "").strip()
    title = os.environ.get("PUCE_MOCAP_OPENROUTER_TITLE", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-OpenRouter-Title"] = title

    req = request.Request(
        os.environ.get("PUCE_MOCAP_OPENROUTER_URL", DEFAULT_OPENROUTER_URL),
        data=data,
        headers=headers,
        method="POST",
    )
    with request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
        raw_response = response.read().decode("utf-8")
    parsed = json.loads(raw_response)
    text = _message_content(parsed)
    interpretation = parse_interpretation_json(text, provider="openrouter_remoto")
    if interpretation_has_prohibited_terms(interpretation):
        return deterministic
    return interpretation


def _message_content(parsed: object) -> str:
    if not isinstance(parsed, dict):
        raise ValueError("La respuesta de OpenRouter no es un objeto JSON.")
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("La respuesta de OpenRouter no contiene choices.")
    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("La primera opcion de OpenRouter no es valida.")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ValueError("La respuesta de OpenRouter no contiene message.")
    content = str(message.get("content", "")).strip()
    if not content:
        raise ValueError("La respuesta de OpenRouter no contiene contenido.")
    return content
