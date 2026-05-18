<p align="center">
    <img src="https://github.com/freemocap/freemocap/assets/15314521/da1af7fe-f808-43dc-8f59-c579715d6593" height="180" alt="FreeMoCap Logo">
</p>

<h2 align="center">PUCE MoCap Fisioterapia — Fe y Alegría</h2>

<h4 align="center">
Sistema de captura de movimiento para apoyar procesos de rehabilitación fisioterapéutica comunitaria, basado en FreeMoCap.
</h4>

---

## Descripción del proyecto

Este proyecto consiste en la adaptación de FreeMoCap para crear un sistema de captura y análisis de movimiento orientado a fisioterapia comunitaria.

El sistema busca apoyar la evaluación de ejercicios físicos, movimientos terapéuticos y análisis de marcha mediante cámaras convencionales, cálculo de ángulos articulares y generación de reportes básicos para seguimiento fisioterapéutico.

El proyecto se desarrolla como parte del programa de Vinculación con la Comunidad de la Pontificia Universidad Católica del Ecuador, en colaboración con Fe y Alegría Ecuador.

---

## Créditos y origen del proyecto

Este repositorio es un fork y adaptación del proyecto original:

**FreeMoCap — Free Motion Capture for Everyone**  
Repositorio original: https://github.com/freemocap/freemocap  
Sitio web: https://freemocap.org  

FreeMoCap fue desarrollado por Jon Matthis y el equipo FreeMoCap.

La licencia original del proyecto es **AGPLv3**, la cual se mantiene en este fork.

---

## Identificación institucional

- Institución: Pontificia Universidad Católica del Ecuador
- Programa: Vinculación con la Comunidad
- Contraparte: Fe y Alegría Ecuador
- Año: 2026

---

## Estudiante desarrollador

- Nombre: Jossue Hermel Gallardo Toro
- Carrera: Ingeniería en Sistemas de Información
- Tutor: [Colocar nombre del tutor]

---

## Logo institucional

> Agregar los logos institucionales en la carpeta `assets`.

![PUCE Logo](assets/logo_puce.png)

![Fe y Alegría Logo](assets/logo_fe_alegria.png)

---

## Objetivo general

Adaptar un sistema de captura de movimiento basado en FreeMoCap para analizar movimientos corporales en ejercicios físicos, rehabilitación fisioterapéutica y marcha en caminadora, con el propósito de apoyar procesos de evaluación y seguimiento en comunidades con recursos limitados.

---

## Módulos del proyecto

### Módulo 1: Sistema de análisis de ejercicios con pesas

Este módulo permite analizar ejercicios físicos básicos mediante captura de movimiento y cálculo de ángulos articulares.

Ejercicios considerados:

- Sentadilla
- Press de hombro
- Peso muerto

Funciones principales:

- Captura del movimiento con cámara.
- Extracción del esqueleto 3D.
- Cálculo de ángulos articulares.
- Indicador visual de postura correcta o incorrecta.
- Reporte básico por sesión.

---

### Módulo 2: Adaptación a rehabilitación fisioterapéutica

Este módulo adapta el sistema a ejercicios de fisioterapia, donde los rangos de movimiento dependen del paciente y de la lesión.

Ejercicios considerados:

- Flexión de codo
- Abducción de hombro
- Rotación de muñeca
- Extensión de rodilla
- Dorsiflexión de tobillo
- Elevación de pierna recta

Funciones principales:

- Perfiles de pacientes en formato JSON.
- Ángulos configurables por paciente.
- Registro de progreso por sesión.
- Reporte en PDF o CSV.

---

### Módulo 3: Análisis de marcha en caminadora

Este módulo permite analizar la marcha de una persona usando varias cámaras y métricas de movimiento.

Métricas consideradas:

- Inclinación del tronco.
- Ángulo de rodillas.
- Simetría entre pierna izquierda y derecha.
- Longitud del paso.
- Indicadores básicos de riesgo de caída.

Funciones principales:

- Captura con 2 o 3 cámaras.
- Calibración con tablero ChArUco.
- Visualización del esqueleto en tiempo real.
- Panel de métricas.
- Semáforo de alertas.
- Reporte final de sesión.

---

## Tecnologías utilizadas

- Python 3.10+
- FreeMoCap
- NumPy
- OpenCV
- Matplotlib
- JSON
- GitHub

---

## Instalación base de FreeMoCap

Para instalar FreeMoCap se puede utilizar el siguiente comando:

```bash
pip install freemocap
