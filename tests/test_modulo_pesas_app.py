from puce_mocap.modulo_pesas_app import (
    LANDMARKS_POSTURA_BASE,
    describir_calidad_global,
    dividir_texto,
    formatear_duracion,
    postura_completa,
)


def esqueleto_base_completo():
    esqueleto = {nombre: [0.0, 0.0, 0.0] for nombre in LANDMARKS_POSTURA_BASE}
    esqueleto.update(
        {
            "right_shoulder": [0.0, 1.0, 0.0],
            "right_elbow": [0.0, 1.5, 0.0],
            "right_wrist": [0.0, 2.0, 0.0],
        }
    )
    return esqueleto


def test_formatear_duracion_usa_horas_minutos_y_segundos():
    assert formatear_duracion(0) == "00:00:00"
    assert formatear_duracion(65) == "00:01:05"
    assert formatear_duracion(3661) == "01:01:01"


def test_describir_calidad_global_sin_diagnosticos():
    assert describir_calidad_global(0.0, 0) == "N/D"
    assert describir_calidad_global(80.0, 20) == "Buena"
    assert describir_calidad_global(55.0, 20) == "En progreso"
    assert describir_calidad_global(20.0, 20) == "Revisar tecnica"


def test_dividir_texto_genera_lineas_para_paneles_angostos():
    lineas = dividir_texto(
        "Alejate de la camara hasta que se vean cabeza cadera rodillas tobillos y pies",
        ancho_maximo=230,
        escala=0.5,
        grosor=1,
    )

    assert len(lineas) > 1
    assert " ".join(lineas).startswith("Alejate de la camara")


def test_postura_completa_exige_landmarks_de_cuerpo_y_ejercicio():
    esqueleto = esqueleto_base_completo()

    assert postura_completa(esqueleto, "Sentadilla")
    assert postura_completa(esqueleto, "Press de hombro")

    esqueleto.pop("left_foot")

    assert not postura_completa(esqueleto, "Sentadilla")
