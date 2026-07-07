"""Adaptador opcional para redactar reportes con LFM local via Ollama."""

from __future__ import annotations

import json
import os
from urllib import request

from puce_mocap.report_llm_common import build_prompt, parse_interpretation_json
from puce_mocap.report_interpreter import (
    ReportInterpretation,
    interpretation_has_prohibited_terms,
)


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_LFM_MODEL = "hf.co/LiquidAI/LFM2.5-350M-GGUF:Q4_K_M"
TIMEOUT_SECONDS = 8


def build_lfm_interpretation(
    kind: str,
    rows: list[dict[str, str]],
    deterministic: ReportInterpretation,
) -> ReportInterpretation:
    """Pide a Ollama una redaccion breve y vuelve al texto local si algo falla."""
    payload = {
        "model": os.environ.get("PUCE_MOCAP_LFM_MODEL", DEFAULT_LFM_MODEL),
        "prompt": build_prompt(kind, rows, deterministic),
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.7,
            "num_predict": 280,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        os.environ.get("PUCE_MOCAP_LFM_OLLAMA_URL", DEFAULT_OLLAMA_URL),
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
        raw_response = response.read().decode("utf-8")
    parsed = json.loads(raw_response)
    text = str(parsed.get("response", "")).strip()
    interpretation = parse_interpretation_json(text, provider="lfm_ollama_local")
    if interpretation_has_prohibited_terms(interpretation):
        return deterministic
    return interpretation
