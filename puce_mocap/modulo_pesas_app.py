"""Aplicacion final de Semana 3 / Modulo 1: ejercicios con pesas en vivo.

Este modulo mantiene la logica PUCE separada del nucleo de FreeMoCap y usa
MediaPipe Pose solo como complemento para el prototipo con camara en vivo.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Callable, Mapping, Sequence

import cv2
import numpy as np

from puce_mocap.exercise_report import generar_reporte_csv
from puce_mocap.exercise_rules import (
    COLOR_ROJO,
    ESTADO_CORREGIR,
    ExerciseFeedback,
    evaluar_peso_muerto,
    evaluar_press_hombro,
    evaluar_sentadilla,
)
from puce_mocap.exercise_session import ExerciseSession

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover - se valida manualmente en Windows
    mp = None


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "assets"
REPORTE_LIVE_PATH = REPO_ROOT / "reports" / "semana_3_live_pose_report.csv"

VENTANA_TITULO = "PUCE MoCap - Modulo de Pesas"
SUBTITULO = "Basado en FreeMoCap | MediaPipe Pose como complemento en vivo"
MENSAJE_POSTURA_INCOMPLETA = "Alejate de la camara hasta que se vean cabeza, cadera, rodillas, tobillos y pies."

ANCHO_DASHBOARD = 1600
ALTO_DASHBOARD = 900

COLOR_FONDO_SUPERIOR = np.array([24, 18, 10], dtype=np.float32)
COLOR_FONDO_INFERIOR = np.array([35, 38, 16], dtype=np.float32)
COLOR_TARJETA = (35, 44, 28)
COLOR_TARJETA_SUAVE = (43, 53, 34)
COLOR_BORDE = (66, 78, 55)
COLOR_TEXTO = (245, 246, 248)
COLOR_TEXTO_SUAVE = (190, 201, 210)
COLOR_CYAN = (232, 192, 27)
COLOR_CYAN_OSCURO = (98, 73, 19)
COLOR_VERDE = (98, 226, 97)
COLOR_VERDE_OSCURO = (48, 92, 40)
COLOR_ROJO_UI = (68, 72, 240)
COLOR_ROJO_OSCURO = (48, 34, 88)
COLOR_AZUL = (238, 130, 62)


Evaluador = Callable[..., ExerciseFeedback]


@dataclass(frozen=True)
class EjercicioConfig:
    """Configuracion visual y funcional de un ejercicio del Modulo 1."""

    tecla: str
    nombre: str
    evaluador: Evaluador
    angulo_principal: str


EJERCICIOS: dict[str, EjercicioConfig] = {
    "1": EjercicioConfig("1", "Sentadilla", evaluar_sentadilla, "angulo_rodilla"),
    "2": EjercicioConfig("2", "Press de hombro", evaluar_press_hombro, "angulo_codo"),
    "3": EjercicioConfig("3", "Peso muerto", evaluar_peso_muerto, "desviacion_tronco"),
}

LANDMARKS_POSTURA_BASE = (
    "nose",
    "right_hip",
    "left_hip",
    "right_knee",
    "left_knee",
    "right_ankle",
    "left_ankle",
    "right_foot",
    "left_foot",
)

LANDMARKS_REQUERIDOS = {
    "Sentadilla": LANDMARKS_POSTURA_BASE + ("right_shoulder",),
    "Press de hombro": LANDMARKS_POSTURA_BASE + ("right_shoulder", "right_elbow", "right_wrist"),
    "Peso muerto": LANDMARKS_POSTURA_BASE + ("right_shoulder",),
}


def formatear_duracion(segundos: float) -> str:
    """Convierte segundos a formato HH:MM:SS para la tarjeta de sesion."""
    segundos_enteros = max(0, int(segundos))
    horas, resto = divmod(segundos_enteros, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


def describir_calidad_global(porcentaje_correcto: float, total_frames: int) -> str:
    """Entrega una etiqueta simple, no clinica, para resumir la sesion."""
    if total_frames == 0:
        return "N/D"
    if porcentaje_correcto >= 75.0:
        return "Buena"
    if porcentaje_correcto >= 50.0:
        return "En progreso"
    return "Revisar tecnica"


def dividir_texto(texto: str, ancho_maximo: int, escala: float, grosor: int) -> list[str]:
    """Divide texto para que entre en un ancho aproximado de OpenCV."""
    palabras = texto.split()
    if not palabras:
        return []

    lineas: list[str] = []
    linea_actual = palabras[0]
    for palabra in palabras[1:]:
        candidata = f"{linea_actual} {palabra}"
        ancho = cv2.getTextSize(candidata, cv2.FONT_HERSHEY_SIMPLEX, escala, grosor)[0][0]
        if ancho <= ancho_maximo:
            linea_actual = candidata
        else:
            lineas.append(linea_actual)
            linea_actual = palabra
    lineas.append(linea_actual)
    return lineas


def postura_completa(esqueleto: Mapping[str, Sequence[float]], ejercicio: str) -> bool:
    """Valida que existan los landmarks minimos antes de evaluar y registrar frames."""
    requeridos = LANDMARKS_REQUERIDOS[ejercicio]
    return all(nombre in esqueleto for nombre in requeridos)


def _feedback_incompleto(ejercicio: str) -> ExerciseFeedback:
    return ExerciseFeedback(
        ejercicio=ejercicio,
        estado=ESTADO_CORREGIR,
        color=COLOR_ROJO,
        angulos={},
        mensajes=[MENSAJE_POSTURA_INCOMPLETA],
    )


def _punto_landmark(landmarks, landmark_id: int, min_visibility: float = 0.35) -> list[float] | None:
    landmark = landmarks[landmark_id]
    if getattr(landmark, "visibility", 1.0) < min_visibility:
        return None
    return [float(landmark.x), float(-landmark.y), float(-landmark.z)]


def mediapipe_a_esqueleto_3d(pose_landmarks) -> dict[str, list[float]]:
    """Convierte landmarks de MediaPipe Pose al formato usado por exercise_rules."""
    if mp is None:  # pragma: no cover - main no llama esta funcion sin MediaPipe
        return {}

    mp_pose = mp.solutions.pose
    landmarks = pose_landmarks.landmark
    mapa = {
        "nose": mp_pose.PoseLandmark.NOSE.value,
        "right_shoulder": mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
        "left_shoulder": mp_pose.PoseLandmark.LEFT_SHOULDER.value,
        "right_elbow": mp_pose.PoseLandmark.RIGHT_ELBOW.value,
        "left_elbow": mp_pose.PoseLandmark.LEFT_ELBOW.value,
        "right_wrist": mp_pose.PoseLandmark.RIGHT_WRIST.value,
        "left_wrist": mp_pose.PoseLandmark.LEFT_WRIST.value,
        "right_hip": mp_pose.PoseLandmark.RIGHT_HIP.value,
        "left_hip": mp_pose.PoseLandmark.LEFT_HIP.value,
        "right_knee": mp_pose.PoseLandmark.RIGHT_KNEE.value,
        "left_knee": mp_pose.PoseLandmark.LEFT_KNEE.value,
        "right_ankle": mp_pose.PoseLandmark.RIGHT_ANKLE.value,
        "left_ankle": mp_pose.PoseLandmark.LEFT_ANKLE.value,
        "right_foot": mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value,
        "left_foot": mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value,
    }

    esqueleto = {}
    for nombre, landmark_id in mapa.items():
        punto = _punto_landmark(landmarks, landmark_id)
        if punto is not None:
            esqueleto[nombre] = punto
    return esqueleto


def evaluar_esqueleto(ejercicio: EjercicioConfig, esqueleto: Mapping[str, Sequence[float]]) -> ExerciseFeedback:
    """Evalua un esqueleto valido con las reglas ya implementadas del Modulo 1."""
    if not postura_completa(esqueleto, ejercicio.nombre):
        return _feedback_incompleto(ejercicio.nombre)

    try:
        if ejercicio.nombre == "Press de hombro":
            return ejercicio.evaluador(esqueleto, lado="right")
        return ejercicio.evaluador(esqueleto)
    except ValueError:
        return _feedback_incompleto(ejercicio.nombre)


def _crear_fondo(ancho: int, alto: int) -> np.ndarray:
    mezcla = np.linspace(0.0, 1.0, alto, dtype=np.float32)[:, None]
    filas = COLOR_FONDO_SUPERIOR * (1.0 - mezcla) + COLOR_FONDO_INFERIOR * mezcla
    return np.repeat(filas[:, None, :], ancho, axis=1).astype(np.uint8)


def _dibujar_rectangulo_redondeado(
    imagen: np.ndarray,
    x: int,
    y: int,
    ancho: int,
    alto: int,
    radio: int,
    color: tuple[int, int, int] | int,
    grosor: int = -1,
) -> None:
    radio = max(0, min(radio, ancho // 2, alto // 2))
    if grosor < 0:
        cv2.rectangle(imagen, (x + radio, y), (x + ancho - radio, y + alto), color, -1)
        cv2.rectangle(imagen, (x, y + radio), (x + ancho, y + alto - radio), color, -1)
        cv2.circle(imagen, (x + radio, y + radio), radio, color, -1)
        cv2.circle(imagen, (x + ancho - radio, y + radio), radio, color, -1)
        cv2.circle(imagen, (x + radio, y + alto - radio), radio, color, -1)
        cv2.circle(imagen, (x + ancho - radio, y + alto - radio), radio, color, -1)
        return

    cv2.line(imagen, (x + radio, y), (x + ancho - radio, y), color, grosor, cv2.LINE_AA)
    cv2.line(imagen, (x + radio, y + alto), (x + ancho - radio, y + alto), color, grosor, cv2.LINE_AA)
    cv2.line(imagen, (x, y + radio), (x, y + alto - radio), color, grosor, cv2.LINE_AA)
    cv2.line(imagen, (x + ancho, y + radio), (x + ancho, y + alto - radio), color, grosor, cv2.LINE_AA)
    cv2.ellipse(imagen, (x + radio, y + radio), (radio, radio), 180, 0, 90, color, grosor, cv2.LINE_AA)
    cv2.ellipse(imagen, (x + ancho - radio, y + radio), (radio, radio), 270, 0, 90, color, grosor, cv2.LINE_AA)
    cv2.ellipse(
        imagen, (x + ancho - radio, y + alto - radio), (radio, radio), 0, 0, 90, color, grosor, cv2.LINE_AA
    )
    cv2.ellipse(imagen, (x + radio, y + alto - radio), (radio, radio), 90, 0, 90, color, grosor, cv2.LINE_AA)


def _dibujar_texto(
    imagen: np.ndarray,
    texto: str,
    x: int,
    y: int,
    escala: float,
    color: tuple[int, int, int] = COLOR_TEXTO,
    grosor: int = 1,
) -> None:
    cv2.putText(imagen, texto, (x, y), cv2.FONT_HERSHEY_SIMPLEX, escala, color, grosor, cv2.LINE_AA)


def _dibujar_texto_centrado(
    imagen: np.ndarray,
    texto: str,
    centro_x: int,
    y: int,
    escala: float,
    color: tuple[int, int, int] = COLOR_TEXTO,
    grosor: int = 1,
) -> None:
    ancho = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala, grosor)[0][0]
    _dibujar_texto(imagen, texto, centro_x - ancho // 2, y, escala, color, grosor)


def _redimensionar_contenido(imagen: np.ndarray, ancho_destino: int, alto_destino: int) -> np.ndarray:
    alto, ancho = imagen.shape[:2]
    escala = min(ancho_destino / ancho, alto_destino / alto)
    nuevo_ancho = max(1, int(ancho * escala))
    nuevo_alto = max(1, int(alto * escala))
    return cv2.resize(imagen, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_AREA)


def _redimensionar_cover(imagen: np.ndarray, ancho_destino: int, alto_destino: int) -> np.ndarray:
    alto, ancho = imagen.shape[:2]
    escala = max(ancho_destino / ancho, alto_destino / alto)
    nuevo_ancho = max(1, int(ancho * escala))
    nuevo_alto = max(1, int(alto * escala))
    redimensionada = cv2.resize(imagen, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_AREA)
    inicio_x = max(0, (nuevo_ancho - ancho_destino) // 2)
    inicio_y = max(0, (nuevo_alto - alto_destino) // 2)
    return redimensionada[inicio_y : inicio_y + alto_destino, inicio_x : inicio_x + ancho_destino]


def _superponer_imagen(base: np.ndarray, imagen: np.ndarray, x: int, y: int) -> None:
    alto, ancho = imagen.shape[:2]
    if x >= base.shape[1] or y >= base.shape[0]:
        return

    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(base.shape[1], x + ancho)
    y2 = min(base.shape[0], y + alto)
    if x1 >= x2 or y1 >= y2:
        return

    recorte = imagen[y1 - y : y2 - y, x1 - x : x2 - x]
    roi = base[y1:y2, x1:x2]
    if recorte.ndim == 3 and recorte.shape[2] == 4:
        alpha = recorte[:, :, 3:4].astype(np.float32) / 255.0
        roi[:] = (alpha * recorte[:, :, :3] + (1.0 - alpha) * roi).astype(np.uint8)
    else:
        roi[:] = recorte[:, :, :3]


def _pegar_imagen_redondeada(base: np.ndarray, imagen: np.ndarray, x: int, y: int, ancho: int, alto: int, radio: int) -> None:
    recorte = _redimensionar_cover(imagen, ancho, alto)
    mascara = np.zeros((alto, ancho), dtype=np.uint8)
    _dibujar_rectangulo_redondeado(mascara, 0, 0, ancho - 1, alto - 1, radio, 255, -1)
    roi = base[y : y + alto, x : x + ancho]
    roi[mascara > 0] = recorte[mascara > 0]


def _cargar_logo(ruta: Path, ancho_maximo: int, alto_maximo: int) -> np.ndarray | None:
    if not ruta.exists():
        return None
    logo = cv2.imread(str(ruta), cv2.IMREAD_UNCHANGED)
    if logo is None:
        return None
    return _redimensionar_contenido(logo, ancho_maximo, alto_maximo)


def _dibujar_barra(
    imagen: np.ndarray,
    x: int,
    y: int,
    ancho: int,
    alto: int,
    progreso: float,
    color: tuple[int, int, int],
) -> None:
    _dibujar_rectangulo_redondeado(imagen, x, y, ancho, alto, alto // 2, (45, 58, 61), -1)
    ancho_activo = int(ancho * min(1.0, max(0.0, progreso)))
    if ancho_activo > 0:
        _dibujar_rectangulo_redondeado(imagen, x, y, ancho_activo, alto, alto // 2, color, -1)


def _dibujar_check(imagen: np.ndarray, centro: tuple[int, int], radio: int, color: tuple[int, int, int]) -> None:
    cv2.circle(imagen, centro, radio, color, -1, cv2.LINE_AA)
    x, y = centro
    cv2.line(imagen, (x - radio // 2, y), (x - radio // 8, y + radio // 3), (245, 255, 245), 3, cv2.LINE_AA)
    cv2.line(imagen, (x - radio // 8, y + radio // 3), (x + radio // 2, y - radio // 3), (245, 255, 245), 3, cv2.LINE_AA)


def _dibujar_x(imagen: np.ndarray, centro: tuple[int, int], radio: int, color: tuple[int, int, int]) -> None:
    cv2.circle(imagen, centro, radio, color, -1, cv2.LINE_AA)
    x, y = centro
    cv2.line(imagen, (x - radio // 3, y - radio // 3), (x + radio // 3, y + radio // 3), (245, 245, 255), 3, cv2.LINE_AA)
    cv2.line(imagen, (x + radio // 3, y - radio // 3), (x - radio // 3, y + radio // 3), (245, 245, 255), 3, cv2.LINE_AA)


class ModuloPesasDashboard:
    """Renderer OpenCV para el dashboard profesional del Modulo 1."""

    def __init__(self, ancho: int = ANCHO_DASHBOARD, alto: int = ALTO_DASHBOARD, assets_dir: Path = ASSETS_DIR):
        self.ancho = ancho
        self.alto = alto
        self.logo_puce = _cargar_logo(assets_dir / "logo_puce.png", 335, 92)
        self.logo_fe_alegria = _cargar_logo(assets_dir / "logo_fe_alegria.png", 96, 96)

    def render(
        self,
        frame_camara: np.ndarray,
        ejercicio: EjercicioConfig,
        feedback: ExerciseFeedback,
        sesion: ExerciseSession,
        segundos_sesion: float,
    ) -> np.ndarray:
        lienzo = _crear_fondo(self.ancho, self.alto)
        self._dibujar_header(lienzo)
        self._dibujar_panel_camara(lienzo, frame_camara)
        self._dibujar_panel_estado(lienzo, ejercicio, feedback)
        self._dibujar_panel_ejercicios(lienzo, ejercicio)
        self._dibujar_panel_metricas(lienzo, sesion)
        self._dibujar_panel_leyenda(lienzo)
        self._dibujar_panel_sesion(lienzo, sesion, segundos_sesion)
        return lienzo

    def _dibujar_header(self, lienzo: np.ndarray) -> None:
        if self.logo_puce is not None:
            _superponer_imagen(lienzo, self.logo_puce, 38, 66)
        else:
            _dibujar_texto(lienzo, "Pontificia Universidad", 40, 92, 0.65, COLOR_CYAN, 2)
            _dibujar_texto(lienzo, "Catolica del Ecuador", 40, 122, 0.65, COLOR_CYAN, 2)

        _dibujar_texto_centrado(lienzo, "PUCE MoCap - Modulo de Pesas", self.ancho // 2, 100, 1.28, COLOR_TEXTO, 3)
        _dibujar_texto_centrado(lienzo, SUBTITULO, self.ancho // 2, 140, 0.62, COLOR_TEXTO_SUAVE, 2)

        if self.logo_fe_alegria is not None:
            _superponer_imagen(lienzo, self.logo_fe_alegria, self.ancho - 290, 58)
        else:
            _dibujar_x(lienzo, (self.ancho - 242, 104), 46, COLOR_ROJO_UI)
        _dibujar_texto(lienzo, "Fe y Alegria", self.ancho - 180, 102, 0.75, COLOR_TEXTO, 2)
        _dibujar_texto(lienzo, "Ecuador", self.ancho - 180, 134, 0.75, COLOR_TEXTO, 2)

    def _dibujar_panel_camara(self, lienzo: np.ndarray, frame_camara: np.ndarray) -> None:
        x, y, w, h = 24, 170, 770, 520
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 18, COLOR_TARJETA, -1)
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 18, COLOR_BORDE, 1)
        _pegar_imagen_redondeada(lienzo, frame_camara, x + 14, y + 14, w - 28, h - 28, 14)
        _dibujar_rectangulo_redondeado(lienzo, x + 24, y + 28, 105, 36, 15, (40, 43, 43), -1)
        cv2.circle(lienzo, (x + 45, y + 46), 6, COLOR_VERDE, -1, cv2.LINE_AA)
        _dibujar_texto(lienzo, "EN VIVO", x + 60, y + 53, 0.48, COLOR_TEXTO, 2)

    def _dibujar_panel_estado(self, lienzo: np.ndarray, ejercicio: EjercicioConfig, feedback: ExerciseFeedback) -> None:
        x, y, w, h = 815, 170, 440, 410
        estado_correcto = feedback.es_correcto
        color_estado = COLOR_VERDE if estado_correcto else COLOR_ROJO_UI
        color_estado_oscuro = COLOR_VERDE_OSCURO if estado_correcto else COLOR_ROJO_OSCURO
        etiqueta_estado = "VERDE / CORRECTO" if estado_correcto else "ROJO / CORREGIR_POSTURA"

        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 18, COLOR_TARJETA, -1)
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 18, COLOR_BORDE, 1)
        cv2.circle(lienzo, (x + 42, y + 42), 22, COLOR_CYAN_OSCURO, -1, cv2.LINE_AA)
        _dibujar_texto(lienzo, "M1", x + 26, y + 51, 0.55, COLOR_CYAN, 2)
        _dibujar_texto(lienzo, "EJERCICIO ACTUAL", x + 75, y + 42, 0.48, COLOR_TEXTO_SUAVE, 2)
        _dibujar_texto(lienzo, f"Ejercicio: {ejercicio.nombre}", x + 75, y + 88, 0.84, COLOR_TEXTO, 2)

        _dibujar_texto(lienzo, "Angulo principal", x + 75, y + 132, 0.55, COLOR_TEXTO_SUAVE, 1)
        valor_angulo = feedback.angulos.get(ejercicio.angulo_principal)
        self._dibujar_angulo_principal(lienzo, x + 75, y + 205, valor_angulo, color_estado)

        _dibujar_rectangulo_redondeado(lienzo, x + 72, y + 225, 322, 58, 10, color_estado_oscuro, -1)
        _dibujar_rectangulo_redondeado(lienzo, x + 72, y + 225, 322, 58, 10, color_estado, 1)
        if estado_correcto:
            _dibujar_check(lienzo, (x + 105, y + 254), 16, color_estado)
        else:
            _dibujar_x(lienzo, (x + 105, y + 254), 16, color_estado)
        _dibujar_texto(lienzo, etiqueta_estado, x + 136, y + 263, 0.65, COLOR_TEXTO, 2)

        mensaje = feedback.mensajes[0] if feedback.mensajes else "Sesion iniciada."
        lineas = dividir_texto(mensaje, 330, 0.56, 1)
        if estado_correcto:
            _dibujar_check(lienzo, (x + 52, y + 334), 15, (42, 168, 70))
        else:
            _dibujar_x(lienzo, (x + 52, y + 334), 15, color_estado)
        for indice, linea in enumerate(lineas[:3]):
            _dibujar_texto(lienzo, linea, x + 75, y + 322 + indice * 31, 0.56, COLOR_TEXTO, 1)

    def _dibujar_angulo_principal(
        self, lienzo: np.ndarray, x: int, y_base: int, valor: float | None, color: tuple[int, int, int]
    ) -> None:
        if valor is None:
            _dibujar_texto(lienzo, "N/D", x, y_base, 1.9, color, 4)
            return

        texto = f"{valor:.0f}"
        escala = 2.15
        grosor = 5
        _dibujar_texto(lienzo, texto, x, y_base, escala, color, grosor)
        ancho_texto, alto_texto = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala, grosor)[0]
        cv2.circle(lienzo, (x + ancho_texto + 18, y_base - alto_texto + 14), 8, color, 3, cv2.LINE_AA)

    def _dibujar_panel_ejercicios(self, lienzo: np.ndarray, ejercicio: EjercicioConfig) -> None:
        x, y, w, h = 1275, 170, 300, 430
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 18, COLOR_TARJETA, -1)
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 18, COLOR_BORDE, 1)
        _dibujar_texto(lienzo, "EJERCICIOS", x + 32, y + 43, 0.52, COLOR_TEXTO_SUAVE, 2)

        for indice, config in enumerate(EJERCICIOS.values()):
            boton_y = y + 68 + indice * 72
            seleccionado = config.tecla == ejercicio.tecla
            relleno = (69, 82, 44) if seleccionado else COLOR_TARJETA_SUAVE
            borde = COLOR_CYAN if seleccionado else (70, 82, 66)
            _dibujar_rectangulo_redondeado(lienzo, x + 20, boton_y, w - 40, 58, 9, relleno, -1)
            _dibujar_rectangulo_redondeado(lienzo, x + 20, boton_y, w - 40, 58, 9, borde, 2 if seleccionado else 1)
            _dibujar_texto(lienzo, config.tecla, x + 60, boton_y + 37, 0.62, COLOR_TEXTO, 2)
            _dibujar_texto(lienzo, config.nombre, x + 92, boton_y + 37, 0.55, COLOR_TEXTO, 2)

        _dibujar_rectangulo_redondeado(lienzo, x + 20, y + 312, w - 40, 58, 9, COLOR_TARJETA_SUAVE, -1)
        _dibujar_rectangulo_redondeado(lienzo, x + 20, y + 312, w - 40, 58, 9, COLOR_AZUL, 1)
        cv2.circle(lienzo, (x + 62, y + 341), 11, COLOR_AZUL, 2, cv2.LINE_AA)
        _dibujar_texto(lienzo, "Reiniciar", x + 96, y + 350, 0.55, (235, 182, 118), 2)

        _dibujar_rectangulo_redondeado(lienzo, x + 20, y + 382, w - 40, 58, 9, (40, 31, 47), -1)
        _dibujar_rectangulo_redondeado(lienzo, x + 20, y + 382, w - 40, 58, 9, COLOR_ROJO_UI, 1)
        cv2.circle(lienzo, (x + 62, y + 411), 11, COLOR_ROJO_UI, 2, cv2.LINE_AA)
        _dibujar_texto(lienzo, "Salir", x + 96, y + 420, 0.55, COLOR_ROJO_UI, 2)

    def _dibujar_panel_metricas(self, lienzo: np.ndarray, sesion: ExerciseSession) -> None:
        x, y, w, h = 815, 600, 440, 110
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 15, COLOR_TARJETA, -1)
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 15, COLOR_BORDE, 1)
        ancho_columna = w // 3
        for divisor in (1, 2):
            cv2.line(lienzo, (x + divisor * ancho_columna, y + 12), (x + divisor * ancho_columna, y + h - 12), COLOR_BORDE, 1)

        porcentaje = sesion.porcentaje_correcto
        metricas = [
            ("REPS", str(sesion.repeticiones), COLOR_TEXTO),
            ("CORRECTO", f"{porcentaje:.0f}%", COLOR_VERDE),
            ("FRAMES", str(sesion.total_frames), COLOR_TEXTO),
        ]
        for indice, (titulo, valor, color) in enumerate(metricas):
            col_x = x + indice * ancho_columna
            _dibujar_texto_centrado(lienzo, titulo, col_x + ancho_columna // 2, y + 34, 0.45, COLOR_TEXTO_SUAVE, 2)
            _dibujar_texto_centrado(lienzo, valor, col_x + ancho_columna // 2, y + 80, 0.96, color, 3)
        _dibujar_barra(lienzo, x + ancho_columna + 30, y + 88, ancho_columna - 60, 9, porcentaje / 100.0, COLOR_VERDE)

    def _dibujar_panel_leyenda(self, lienzo: np.ndarray) -> None:
        x, y, w, h = 24, 720, 700, 150
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 16, COLOR_TARJETA, -1)
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 16, COLOR_BORDE, 1)
        _dibujar_texto(lienzo, "LEYENDA DE ESTADO", x + 34, y + 34, 0.5, COLOR_TEXTO_SUAVE, 2)

        self._dibujar_tarjeta_leyenda(lienzo, x + 34, y + 58, 275, "VERDE = CORRECTO", "Ejercicio ejecutado con buena tecnica.", True)
        self._dibujar_tarjeta_leyenda(
            lienzo, x + 330, y + 58, 330, "ROJO = CORREGIR POSTURA", "Ajusta la postura y vuelve a intentar.", False
        )

    def _dibujar_tarjeta_leyenda(
        self, lienzo: np.ndarray, x: int, y: int, w: int, titulo: str, detalle: str, correcto: bool
    ) -> None:
        color = COLOR_VERDE if correcto else COLOR_ROJO_UI
        fondo = COLOR_VERDE_OSCURO if correcto else COLOR_ROJO_OSCURO
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, 76, 10, fondo, -1)
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, 76, 10, color, 1)
        if correcto:
            _dibujar_check(lienzo, (x + 36, y + 38), 18, color)
        else:
            _dibujar_x(lienzo, (x + 36, y + 38), 18, color)
        _dibujar_texto(lienzo, titulo, x + 72, y + 30, 0.47, color, 2)
        for indice, linea in enumerate(dividir_texto(detalle, w - 90, 0.42, 1)[:2]):
            _dibujar_texto(lienzo, linea, x + 72, y + 55 + indice * 20, 0.42, COLOR_TEXTO, 1)

    def _dibujar_panel_sesion(self, lienzo: np.ndarray, sesion: ExerciseSession, segundos_sesion: float) -> None:
        x, y, w, h = 745, 720, 830, 150
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 16, COLOR_TARJETA, -1)
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, h, 16, COLOR_BORDE, 1)
        _dibujar_texto(lienzo, "SESION EN CURSO", x + 34, y + 34, 0.5, COLOR_TEXTO_SUAVE, 2)

        porcentaje = sesion.porcentaje_correcto
        calidad = describir_calidad_global(porcentaje, sesion.total_frames)
        columnas = [
            ("DURACION", formatear_duracion(segundos_sesion), COLOR_AZUL, min(1.0, segundos_sesion / 900.0)),
            ("PORCENTAJE CORRECTO", f"{porcentaje:.0f}%", COLOR_VERDE, porcentaje / 100.0),
            ("CALIDAD GLOBAL", calidad, COLOR_VERDE if porcentaje >= 75.0 else COLOR_AZUL, porcentaje / 100.0),
        ]
        ancho_columna = 245
        for indice, (titulo, valor, color, progreso) in enumerate(columnas):
            col_x = x + 48 + indice * 260
            if indice > 0:
                cv2.line(lienzo, (col_x - 35, y + 64), (col_x - 35, y + h - 28), COLOR_BORDE, 1)
            cv2.circle(lienzo, (col_x, y + 86), 14, color, 2, cv2.LINE_AA)
            _dibujar_texto(lienzo, titulo, col_x + 36, y + 78, 0.43, COLOR_TEXTO_SUAVE, 1)
            _dibujar_texto(lienzo, valor, col_x + 36, y + 108, 0.62, COLOR_TEXTO, 2)
            _dibujar_barra(lienzo, col_x, y + 122, ancho_columna - 55, 9, progreso, color)


def _reiniciar_sesion(ejercicio: EjercicioConfig) -> tuple[ExerciseSession, float]:
    return ExerciseSession(ejercicio.nombre), time.monotonic()


def main() -> None:
    """Ejecuta la interfaz final del Modulo 1 con camara, pose y reporte CSV."""
    if mp is None:
        print("MediaPipe no esta instalado. Ejecuta: python -m pip install mediapipe")
        return

    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    landmark_spec = mp_drawing.DrawingSpec(color=(80, 255, 90), thickness=2, circle_radius=4)
    connection_spec = mp_drawing.DrawingSpec(color=(60, 215, 240), thickness=2, circle_radius=2)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        print("No se pudo abrir la camara 0. Verifica permisos de camara en Windows.")
        return

    dashboard = ModuloPesasDashboard()
    ejercicio = EJERCICIOS["1"]
    sesion, inicio_sesion = _reiniciar_sesion(ejercicio)

    cv2.namedWindow(VENTANA_TITULO, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(VENTANA_TITULO, dashboard.ancho, dashboard.alto)

    print("PUCE MoCap - Modulo de Pesas iniciado.")
    print("Teclas: 1 Sentadilla | 2 Press hombro | 3 Peso muerto | r Reiniciar | q Salir")

    with mp_pose.Pose(model_complexity=1, min_detection_confidence=0.6, min_tracking_confidence=0.6) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("No se pudo leer un frame de la camara.")
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resultado = pose.process(rgb)

            frame_visual = frame.copy()
            if resultado.pose_landmarks:
                mp_drawing.draw_landmarks(
                    frame_visual,
                    resultado.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=landmark_spec,
                    connection_drawing_spec=connection_spec,
                )
                esqueleto = mediapipe_a_esqueleto_3d(resultado.pose_landmarks)
                feedback = evaluar_esqueleto(ejercicio, esqueleto)
            else:
                feedback = _feedback_incompleto(ejercicio.nombre)

            if feedback.angulos:
                sesion.registrar_feedback(feedback)

            segundos_sesion = time.monotonic() - inicio_sesion
            lienzo = dashboard.render(frame_visual, ejercicio, feedback, sesion, segundos_sesion)
            cv2.imshow(VENTANA_TITULO, lienzo)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord("q"):
                break
            if tecla in (ord("1"), ord("2"), ord("3")):
                ejercicio = EJERCICIOS[chr(tecla)]
                sesion, inicio_sesion = _reiniciar_sesion(ejercicio)
            elif tecla == ord("r"):
                sesion, inicio_sesion = _reiniciar_sesion(ejercicio)

            if cv2.getWindowProperty(VENTANA_TITULO, cv2.WND_PROP_VISIBLE) < 1:
                break

    cap.release()
    cv2.destroyAllWindows()
    REPORTE_LIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    generar_reporte_csv(sesion.exportar_resumen(), REPORTE_LIVE_PATH)
    print(f"Reporte CSV generado: {REPORTE_LIVE_PATH}")


if __name__ == "__main__":
    main()
