import csv
import json

from pypdf import PdfReader

from puce_mocap.pdf_reports import export_pdf_report
from puce_mocap.report_interpreter import build_report_interpretation
from puce_mocap.reports_v2 import (
    INSTITUTIONAL_FIELDS,
    WEIGHTS_FIELDS,
    export_gait_session,
    export_rehab_sessions,
    export_weight_sessions,
    sanitize_csv_value,
)
from puce_mocap.rehab_profiles import crear_perfil_demo


def test_sanitiza_formulas_de_hoja_de_calculo():
    assert sanitize_csv_value("=HYPERLINK('x')") == "'=HYPERLINK('x')"
    assert sanitize_csv_value("Paciente de prueba") == "Paciente de prueba"


def test_reporte_pesas_v2_incluye_contexto_y_session_id(tmp_path):
    path = export_weight_sessions(
        [
            {
                "session_id": "S-1",
                "fecha": "2026-06-21T10:00:00",
                "fuente_datos": "freemocap_session",
                "codigo_paciente": "PAC-001",
                "nombre_paciente": "Paciente ficticio",
                "lesion": "Seguimiento ficticio",
                "observaciones_paciente": "Sin datos reales",
                "ejercicio": "Sentadilla",
                "total_frames": 10,
                "frames_evaluables_forma": 4,
                "frames_correctos": 4,
                "porcentaje_correcto": 100.0,
                "repeticiones": 1,
            }
        ],
        tmp_path / "pesas.csv",
    )

    with path.open(newline="", encoding="utf-8") as stream:
        row = next(csv.DictReader(stream))
    assert row["session_id"] == "S-1"
    assert row["nombre_paciente"] == "Paciente ficticio"
    assert row["institucion"] == "Pontificia Universidad Católica del Ecuador"
    assert row["licencia"] == "AGPLv3"


def test_reporte_pdf_es_legible_y_solo_incluye_la_sesion_mas_reciente(tmp_path):
    csv_path = tmp_path / "pesas_v2.csv"
    common = {
        "fecha": "2026-07-03T10:00:00",
        "fuente_datos": "freemocap_session",
        "codigo_paciente": "PAC-001",
        "nombre_paciente": "Paciente ficticio",
        "lesion": "Seguimiento ficticio",
        "observaciones_paciente": "Sin datos reales",
        "ejercicio": "Sentadilla",
        "total_frames": 10,
        "frames_evaluables_forma": 4,
        "frames_correctos": 4,
        "porcentaje_correcto": 100.0,
        "repeticiones": 1,
    }
    export_weight_sessions([{**common, "session_id": "ANTERIOR"}], csv_path)
    export_weight_sessions([{**common, "session_id": "ACTUAL", "repeticiones": 3}], csv_path)

    pdf_path = export_pdf_report(csv_path)
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() for page in reader.pages)

    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert "Reporte de ejercicios con pesas" in text
    assert "Paciente ficticio" in text
    assert "ACTUAL" in text
    assert "ANTERIOR" not in text
    assert "pucefisiomocap/puce-fisioterapia-mocap" in text
    assert "no sustituye la evaluación de un fisioterapeuta" in text
    assert "Interpretación automática local" in text
    assert "Reglas determinísticas locales" in text
    assert "La sesion de pesas registro 3 repeticiones" in text
    assert "riesgo grave" not in text
    assert "lesión detectada" not in text


def test_migra_csv_antiguo_y_pdf_asocia_umbrales_y_repeticiones_correctamente(tmp_path):
    csv_path = tmp_path / "pesas_v2.csv"
    legacy_fields = INSTITUTIONAL_FIELDS + [
        "session_id", "fecha", "fuente_datos", "ejercicio", "total_frames",
        "frames_evaluables_forma", "frames_correctos", "porcentaje_correcto",
        "repeticiones", "observacion",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=legacy_fields)
        writer.writeheader()
        writer.writerow({"session_id": "LEGACY", "ejercicio": "Sentadilla", "repeticiones": 2})
    corrupted_new_row = {
        "session_id": "CORRUPTED-BY-OLD-HEADER",
        "codigo_paciente": "PAC-RECOVERED",
        "nombre_paciente": "Fila recuperada",
        "ejercicio": "Sentadilla",
        "total_frames": 1,
        "repeticiones": 7,
    }
    with csv_path.open("a", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerow([corrupted_new_row.get(field, "") for field in WEIGHTS_FIELDS])

    export_weight_sessions(
        [{
            "session_id": "S-12",
            "fecha": "2026-07-03T12:00:00",
            "fuente_datos": "navegador_mediapipe",
            "codigo_paciente": "PAC-012",
            "nombre_paciente": "Paciente ficticio",
            "lesion": "Seguimiento ficticio",
            "observaciones_paciente": "Sin datos reales",
            "ejercicio": "Sentadilla",
            "angulo_minimo_inicio": 150,
            "angulo_maximo_inicio": 175,
            "angulo_minimo_objetivo": 65,
            "angulo_maximo_objetivo": 95,
            "total_frames": 600,
            "frames_evaluables_forma": 400,
            "frames_correctos": 350,
            "porcentaje_correcto": 87.5,
            "repeticiones": 12,
        }],
        csv_path,
    )

    with csv_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    assert reader.fieldnames == WEIGHTS_FIELDS
    assert rows[1]["codigo_paciente"] == "PAC-RECOVERED"
    assert rows[1]["repeticiones"] == "7"
    assert rows[-1]["codigo_paciente"] == "PAC-012"
    assert rows[-1]["angulo_minimo_objetivo"] == "65"
    assert rows[-1]["repeticiones"] == "12"

    text = "\n".join(page.extract_text() for page in PdfReader(export_pdf_report(csv_path)).pages)
    assert "Paciente ficticio" in text
    assert "Ángulo objetivo mínimo\n65 grados" in text
    assert "Repeticiones\n12" in text
    assert "Repeticiones\n150" not in text


def test_comparacion_rehab_busca_mismo_paciente_y_ejercicio(tmp_path):
    path = tmp_path / "rehab.csv"
    profile = crear_perfil_demo()
    base = {
        "session_id": "S-1",
        "fecha": "2026-06-01T10:00:00",
        "fuente_datos": "mediapipe_live",
        "codigo_paciente": "PAC-001",
        "ejercicio": "flexion_codo",
        "frames_validos": 10,
        "angulo_maximo_alcanzado": 80.0,
        "repeticiones_estimadas": 1,
        "porcentaje_dentro_rango": 50.0,
    }
    export_rehab_sessions([base], profile, path)
    export_rehab_sessions([{**base, "session_id": "S-2", "angulo_maximo_alcanzado": 90.0}], profile, path)

    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[-1]["comparacion_sesion_anterior"].startswith("Cambio de +10.00")
    assert rows[-1]["nombre_paciente"] == "Paciente de prueba"
    assert rows[-1]["observaciones_paciente"] == "Perfil demo sin datos reales"


def test_pdf_rehabilitacion_incluye_interpretacion_deterministica(tmp_path):
    path = tmp_path / "rehabilitacion_v3.csv"
    profile = crear_perfil_demo()
    export_rehab_sessions(
        [
            {
                "session_id": "R-1",
                "fecha": "2026-07-03T12:00:00",
                "fuente_datos": "mediapipe_live",
                "codigo_paciente": "PAC-001",
                "ejercicio": "flexion_codo",
                "frames_validos": 20,
                "angulo_maximo_alcanzado": 100.0,
                "repeticiones_objetivo": 10,
                "repeticiones_estimadas": 4,
                "porcentaje_dentro_rango": 80.0,
            }
        ],
        profile,
        path,
    )

    text = "\n".join(page.extract_text() for page in PdfReader(export_pdf_report(path)).pages)

    assert "Interpretación automática local" in text
    assert "La sesion de rehabilitacion registro 4 de 10 repeticion" in text
    assert "El angulo maximo alcanzado observado fue 100.0 grados" in text
    assert "No reemplaza la evaluacion de un fisioterapeuta" in text


def test_pdf_marcha_incluye_interpretacion_deterministica(tmp_path):
    path = export_gait_session(
        {
            "session_id": "G-1",
            "fecha": "2026-07-03T12:00:00",
            "fuente_datos": "mediapipe_live",
            "duracion_segundos": 30.0,
            "total_frames": 300,
            "frames_validos": 250,
            "porcentaje_verde": 70.0,
            "porcentaje_amarillo": 20.0,
            "porcentaje_rojo": 10.0,
            "promedio_inclinacion_tronco": 8.0,
            "promedio_asimetria_rodillas": 12.0,
            "promedio_longitud_paso": 0.45,
            "estado_global": "ATENCION",
            "observaciones": ["Asimetría de ciclos mayor a 10 grados; revisar con fisioterapeuta."],
        },
        tmp_path / "marcha_v2.csv",
    )

    text = "\n".join(page.extract_text() for page in PdfReader(export_pdf_report(path)).pages)

    assert "La sesion de marcha tuvo estado general atencion" in text
    assert "Asimetria media entre rodillas: 12.0 grados" in text
    assert "Verificar simetria de rodillas" in text


def test_lfm_desactivado_por_defecto_no_llama_ollama(monkeypatch):
    monkeypatch.delenv("PUCE_MOCAP_REPORT_INTERPRETER", raising=False)

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("No debe llamar Ollama por defecto")

    monkeypatch.setattr("puce_mocap.local_lfm_interpreter.request.urlopen", fail_urlopen)
    interpretation = build_report_interpretation("pesas", [_weights_row()])

    assert interpretation.provider == "deterministico_local"


def test_lfm_opcional_reemplaza_redaccion_y_anonimiza_prompt(monkeypatch):
    monkeypatch.setenv("PUCE_MOCAP_REPORT_INTERPRETER", "lfm_ollama")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            response = {
                "resumen": "Texto LFM local basado en metricas anonimizadas.",
                "hallazgos": ["Hallazgo redactado localmente."],
                "recomendaciones": ["Mantener revision supervisada."],
                "limitaciones": ["Interpretacion de apoyo sin conclusiones clinicas."],
            }
            return json.dumps({"response": json.dumps(response)}).encode("utf-8")

    def fake_urlopen(req, timeout):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("puce_mocap.local_lfm_interpreter.request.urlopen", fake_urlopen)

    interpretation = build_report_interpretation(
        "pesas",
        [
            {
                **_weights_row(),
                "codigo_paciente": "PAC-SECRET",
                "nombre_paciente": "Paciente Secreto",
                "lesion": "Lesion privada",
                "observaciones_paciente": "Observacion privada",
                "session_id": "SESSION-SECRET",
            }
        ],
    )

    assert interpretation.provider == "lfm_ollama_local"
    assert interpretation.resumen.startswith("Texto LFM local")
    prompt = captured["payload"]["prompt"]
    assert "Paciente Secreto" not in prompt
    assert "PAC-SECRET" not in prompt
    assert "Lesion privada" not in prompt
    assert "Observacion privada" not in prompt
    assert "SESSION-SECRET" not in prompt


def test_lfm_fallback_si_respuesta_usa_lenguaje_prohibido(monkeypatch):
    monkeypatch.setenv("PUCE_MOCAP_REPORT_INTERPRETER", "lfm_ollama")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            response = {
                "resumen": "Texto con riesgo grave.",
                "hallazgos": ["Hallazgo no valido."],
                "recomendaciones": ["Mantener revision supervisada."],
                "limitaciones": ["Interpretacion de apoyo."],
            }
            return json.dumps({"response": json.dumps(response)}).encode("utf-8")

    monkeypatch.setattr("puce_mocap.local_lfm_interpreter.request.urlopen", lambda *_args, **_kwargs: FakeResponse())

    interpretation = build_report_interpretation("pesas", [_weights_row()])

    assert interpretation.provider == "deterministico_local"
    assert "riesgo grave" not in interpretation.resumen


def test_openrouter_opcional_reemplaza_redaccion_y_anonimiza_prompt(monkeypatch):
    monkeypatch.setenv("PUCE_MOCAP_REPORT_INTERPRETER", "openrouter")
    monkeypatch.setenv("PUCE_MOCAP_OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("PUCE_MOCAP_OPENROUTER_MODEL", "openrouter/free")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            response = {
                "resumen": "Texto remoto basado en metricas anonimizadas.",
                "hallazgos": ["Hallazgo redactado por el proveedor remoto."],
                "recomendaciones": ["Mantener revision supervisada."],
                "limitaciones": ["Interpretacion de apoyo sin conclusiones clinicas."],
            }
            return json.dumps(
                {"choices": [{"message": {"content": json.dumps(response)}}]}
            ).encode("utf-8")

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["auth"] = req.headers["Authorization"]
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("puce_mocap.openrouter_interpreter.request.urlopen", fake_urlopen)

    interpretation = build_report_interpretation(
        "pesas",
        [
            {
                **_weights_row(),
                "codigo_paciente": "PAC-SECRET",
                "nombre_paciente": "Paciente Secreto",
                "lesion": "Lesion privada",
                "observaciones_paciente": "Observacion privada",
                "session_id": "SESSION-SECRET",
            }
        ],
    )

    assert interpretation.provider == "openrouter_remoto"
    assert interpretation.resumen.startswith("Texto remoto")
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    user_prompt = captured["payload"]["messages"][1]["content"]
    assert "Paciente Secreto" not in user_prompt
    assert "PAC-SECRET" not in user_prompt
    assert "Lesion privada" not in user_prompt
    assert "Observacion privada" not in user_prompt
    assert "SESSION-SECRET" not in user_prompt


def test_openrouter_sin_api_key_vuelve_a_deterministico(monkeypatch):
    monkeypatch.setenv("PUCE_MOCAP_REPORT_INTERPRETER", "openrouter")
    monkeypatch.delenv("PUCE_MOCAP_OPENROUTER_API_KEY", raising=False)

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("No debe llamar OpenRouter sin API key")

    monkeypatch.setattr("puce_mocap.openrouter_interpreter.request.urlopen", fail_urlopen)

    interpretation = build_report_interpretation("pesas", [_weights_row()])

    assert interpretation.provider == "deterministico_local"


def test_openrouter_ignora_configuracion_local_ollama(monkeypatch):
    monkeypatch.setenv("PUCE_MOCAP_REPORT_INTERPRETER", "openrouter")
    monkeypatch.setenv("PUCE_MOCAP_OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("PUCE_MOCAP_OPENROUTER_MODEL", "openrouter/free")
    monkeypatch.setenv("PUCE_MOCAP_LFM_MODEL", "modelo-local-que-no-debe-usarse")
    monkeypatch.setenv("PUCE_MOCAP_LFM_OLLAMA_URL", "http://127.0.0.1:9999/no-usar")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            response = {
                "resumen": "Texto OpenRouter.",
                "hallazgos": ["Hallazgo remoto."],
                "recomendaciones": ["Mantener revision supervisada."],
                "limitaciones": ["Interpretacion de apoyo."],
            }
            return json.dumps(
                {"choices": [{"message": {"content": json.dumps(response)}}]}
            ).encode("utf-8")

    def fail_lfm(*_args, **_kwargs):
        raise AssertionError("No debe invocar el adaptador Ollama cuando se selecciona OpenRouter")

    def fake_openrouter(req, timeout):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("puce_mocap.local_lfm_interpreter.build_lfm_interpretation", fail_lfm)
    monkeypatch.setattr("puce_mocap.openrouter_interpreter.request.urlopen", fake_openrouter)

    interpretation = build_report_interpretation("pesas", [_weights_row()])

    assert interpretation.provider == "openrouter_remoto"
    assert captured["payload"]["model"] == "openrouter/free"


def test_openrouter_fallback_si_respuesta_usa_lenguaje_prohibido(monkeypatch):
    monkeypatch.setenv("PUCE_MOCAP_REPORT_INTERPRETER", "openrouter")
    monkeypatch.setenv("PUCE_MOCAP_OPENROUTER_API_KEY", "sk-test")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            response = {
                "resumen": "Texto con riesgo grave.",
                "hallazgos": ["Hallazgo no valido."],
                "recomendaciones": ["Mantener revision supervisada."],
                "limitaciones": ["Interpretacion de apoyo."],
            }
            return json.dumps(
                {"choices": [{"message": {"content": json.dumps(response)}}]}
            ).encode("utf-8")

    monkeypatch.setattr("puce_mocap.openrouter_interpreter.request.urlopen", lambda *_args, **_kwargs: FakeResponse())

    interpretation = build_report_interpretation("pesas", [_weights_row()])

    assert interpretation.provider == "deterministico_local"
    assert "riesgo grave" not in interpretation.resumen


def _weights_row():
    return {
        "session_id": "S-1",
        "fecha": "2026-07-03T10:00:00",
        "fuente_datos": "freemocap_session",
        "ejercicio": "Sentadilla",
        "total_frames": "100",
        "frames_evaluables_forma": "80",
        "frames_correctos": "70",
        "porcentaje_correcto": "87.5",
        "repeticiones": "8",
        "observacion": "Postura correcta en el punto objetivo.",
    }
