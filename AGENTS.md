# AGENTS.md — PUCE Fisioterapia MoCap

## Propósito del proyecto

Este repositorio es un fork y adaptación de FreeMoCap para desarrollar un sistema de captura y análisis de movimiento orientado a fisioterapia comunitaria dentro del proyecto PUCE — Fe y Alegría.

El objetivo es implementar, de forma incremental, un sistema que permita:
- Analizar ejercicios físicos básicos mediante ángulos articulares.
- Adaptar ejercicios a rehabilitación fisioterapéutica con rangos configurables por paciente.
- Analizar marcha en caminadora usando captura de movimiento.
- Generar reportes simples de sesión para seguimiento fisioterapéutico.
- Mantener créditos, licencia y trazabilidad del proyecto original FreeMoCap.

Este software es una herramienta de apoyo académico/comunitario. No debe presentarse como diagnóstico médico automático. Toda interpretación clínica debe quedar bajo supervisión de un fisioterapeuta.

---

## Contexto institucional obligatorio

Mantener visible esta información en documentación, pantallas principales y reportes cuando corresponda:

- Institución: Pontificia Universidad Católica del Ecuador
- Programa: Vinculación con la Comunidad
- Contraparte: Fe y Alegría Ecuador
- Año: 2026
- Estudiante desarrollador: Jossue Hermel Gallardo Toro
- Carrera: Ingeniería en Sistemas de Información
- Tutor: RODRIGUEZ CLAVIJO FRANCISCO
- Proyecto base: FreeMoCap — Free Motion Capture for Everyone
- Repositorio original: https://github.com/freemocap/freemocap
- Sitio oficial: https://freemocap.org
- Licencia original: AGPLv3

Nunca eliminar créditos, licencia, archivos legales, código de conducta ni referencias al proyecto original FreeMoCap.

---

## Reglas generales para Codex

1. Antes de modificar código, inspeccionar la estructura real del repositorio.
2. No asumir rutas internas de FreeMoCap sin revisar archivos existentes.
3. Hacer cambios pequeños, claros y fáciles de revisar.
4. Priorizar código simple y funcional sobre arquitectura compleja.
5. No romper la ejecución base de FreeMoCap:
   - `python -m freemocap`
   - `freemocap`
6. No modificar dependencias pesadas sin necesidad.
7. No subir datos reales de pacientes, videos pesados, sesiones crudas, entornos virtuales ni archivos temporales.
8. Mantener compatibilidad con Python 3.10+.
9. Escribir nombres, comentarios principales y mensajes de interfaz en español cuando sean parte del proyecto PUCE.
10. Si hay conflicto entre una solución nueva y el funcionamiento original de FreeMoCap, crear un módulo separado en lugar de alterar el núcleo.

---

## Estructura recomendada para las personalizaciones

Usar esta estructura siempre que sea posible, ajustándola solo si la estructura real del repositorio exige otra cosa:

```text
puce-fisioterapia-mocap/
│
├── assets/
│   ├── logo_puce.png
│   └── logo_fe_alegria.png
│
├── docs/
│   ├── cronograma.md
│   ├── guia_uso.md
│   └── demo_casa_abierta.md
│
├── freemocap/
│   └── puce_mocap/
│       ├── __init__.py
│       ├── config.py
│       ├── angle_utils.py
│       ├── exercise_analyzer.py
│       ├── rehab_profiles.py
│       ├── rehab_analyzer.py
│       ├── gait_analyzer.py
│       ├── reports.py
│       └── ui_overlay.py
│
├── tests/
│   └── puce_mocap/
│       ├── test_angle_utils.py
│       ├── test_exercise_analyzer.py
│       ├── test_rehab_profiles.py
│       └── test_gait_analyzer.py
│
├── README.md
├── LICENSE
└── AGENTS.md
```

Si `freemocap/puce_mocap/` no encaja con la arquitectura real, proponer una ruta equivalente y explicar por qué.

---

## Comandos base de trabajo

En Windows:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
python -m freemocap
```

Para pruebas, usar el comando disponible en el repositorio. Si no existe configuración de pruebas, crear pruebas unitarias mínimas con `pytest` para los módulos nuevos:

```powershell
pytest tests
```

No ejecutar comandos destructivos. No borrar carpetas grandes sin confirmación.

---

## Roadmap obligatorio del proyecto

### Semana 1 — Personalización inicial y prueba con una cámara

Entregable:
- Repositorio GitHub personalizado.
- README institucional con créditos.
- Carpeta `assets/` con logos PUCE y Fe y Alegría.
- FreeMoCap instalado y probado con una cámara.

Tareas:
- Revisar README actual.
- Mantener créditos al proyecto original.
- Agregar descripción del proyecto PUCE — Fe y Alegría.
- Verificar que el proyecto se pueda ejecutar.
- No tocar módulos complejos todavía.

---

### Semana 2 — Cálculo de ángulos y datos del esqueleto

Entregable:
- Función de cálculo de ángulos validada.
- Prueba con datos 3D simples.
- Base para usar coordenadas de articulaciones.

Crear o mejorar `angle_utils.py` con funciones como:

```python
def calcular_angulo(punto_a, punto_b, punto_c):
    """Calcula el ángulo en el punto B formado por A-B-C."""
```

Reglas:
- Usar NumPy.
- Manejar vectores con norma cero para evitar errores.
- Retornar ángulos en grados.
- Agregar pruebas unitarias con casos conocidos:
  - 90 grados.
  - 180 grados.
  - 45 grados aproximado.
  - puntos inválidos o con norma cero.

---

### Semana 3 — Módulo de ejercicios con pesas

Entregable:
- Módulo de pesas con indicador correcto/incorrecto.
- Identidad PUCE visible.
- Contador básico de repeticiones.
- Porcentaje de sesión en postura correcta.

Ejercicios mínimos:
1. Sentadilla.
2. Press de hombro.
3. Peso muerto.

Reglas iniciales:

Sentadilla:
- Monitorear rodilla, cadera y tobillo.
- Rodilla entre 70° y 100° en el punto más bajo.
- Advertir si tobillo supera 35°.
- Advertir si cadera baja de 45°.

Press de hombro:
- Monitorear hombro, codo y muñeca.
- Codo cercano a 90° al inicio.
- Brazo extendido entre 170° y 180° arriba.

Peso muerto:
- Monitorear cadera, rodilla y columna.
- Advertir si la espalda se desvía más de 20°.
- Advertir posible colapso de rodillas hacia adentro si se detecta asimetría relevante.

Interfaz:
- Usar mensajes claros en español.
- Verde = correcto.
- Rojo = corregir postura.
- Mostrar el ángulo actual y recomendación breve.

---

### Semana 4 — Análisis de marcha en caminadora

Entregable:
- Módulo de caminadora con métricas en pantalla.
- Semáforo de alertas.
- Cálculo inicial de simetría y longitud de paso.

Métricas mínimas:
- Inclinación del tronco.
- Ángulo de rodilla derecha.
- Ángulo de rodilla izquierda.
- Asimetría entre rodillas.
- Longitud de paso.
- Indicador básico de riesgo o alerta.

Crear o mejorar `gait_analyzer.py` con una función principal parecida a:

```python
def analizar_marcha(esqueleto_3d):
    """Recibe coordenadas 3D de articulaciones y retorna métricas de marcha."""
```

Reglas:
- No afirmar diagnósticos médicos.
- Usar etiquetas como:
  - `normal`
  - `atencion`
  - `revisar_con_fisioterapeuta`
- Marcar asimetría si la diferencia entre rodillas supera 10°.
- Mantener el cálculo desacoplado de la interfaz.

---

### Semana 5 — Rehabilitación fisioterapéutica con perfiles JSON

Entregable:
- Perfiles de paciente en JSON.
- Ejercicios terapéuticos con rangos configurables.
- Reporte CSV o PDF básico.

Ejercicios mínimos:
1. Flexión de codo.
2. Abducción de hombro.
3. Rotación de muñeca.
4. Extensión de rodilla.
5. Dorsiflexión de tobillo.
6. Elevación de pierna recta.

Formato recomendado de perfil:

```json
{
  "nombre": "Paciente de prueba",
  "codigo_paciente": "PAC-001",
  "lesion": "Fractura de radio distal",
  "ejercicios": {
    "flexion_codo": {
      "angulo_minimo": 30,
      "angulo_maximo": 120,
      "repeticiones_objetivo": 10
    }
  }
}
```

Reglas de privacidad:
- Usar pacientes ficticios en ejemplos.
- No guardar nombres reales, cédulas, teléfonos, direcciones ni datos sensibles en el repositorio.
- Los reportes reales deben quedar fuera de Git.

Reportes:
- Priorizar CSV por simplicidad.
- PDF es opcional si ya existe una librería instalada o si se justifica agregar una dependencia ligera.
- Incluir:
  - paciente/código,
  - fecha,
  - ejercicio,
  - ángulo máximo,
  - repeticiones,
  - porcentaje dentro de rango,
  - comparación con sesión anterior si existe.

---

### Semana 6 — Pruebas integrales y ajustes

Entregable:
- Sistema validado en entorno real bajo supervisión.
- Registro de al menos 5 sesiones de prueba, sin datos sensibles en Git.
- Correcciones de errores encontrados.

Tareas:
- Probar módulo de pesas.
- Probar módulo de fisioterapia.
- Probar módulo de caminadora.
- Registrar feedback del fisioterapeuta.
- Ajustar mensajes, rangos y reportes.

---

### Semana 7 — Documentación final y demo

Entregable:
- Repositorio final.
- Demo lista para casa abierta.
- Guía de uso.
- QR del repositorio.
- Video o evidencia de funcionamiento.

Tareas:
- Documentar instalación.
- Documentar cómo ejecutar cada módulo.
- Documentar limitaciones.
- Preparar demo de 5 minutos.
- Verificar que README y licencia estén correctos.

---

## Reglas de implementación de cálculo de ángulos

La función de ángulos debe:
- Aceptar listas, tuplas o arrays NumPy.
- Convertir entradas a `np.array(..., dtype=float)`.
- Verificar que cada punto tenga 2 o 3 coordenadas.
- Manejar división para cero.
- Usar `np.clip(coseno, -1.0, 1.0)`.
- Retornar `float`.

Ejemplo esperado:

```python
angulo_rodilla = calcular_angulo(cadera, rodilla, tobillo)
```

Nunca duplicar la misma fórmula en varios módulos. Reutilizar `angle_utils.py`.

---

## Reglas para interfaz y textos visuales

La interfaz debe ser clara para usuarios no técnicos.

Usar textos como:
- `Postura correcta`
- `Corrige la postura`
- `Dentro del rango terapéutico`
- `Fuera del rango terapéutico`
- `Revisar con fisioterapeuta`
- `Sesión iniciada`
- `Sesión finalizada`

Evitar textos alarmistas como:
- `riesgo grave`
- `diagnóstico`
- `lesión detectada`
- `enfermedad detectada`

---

## Reglas para reportes

Los reportes deben ser simples, legibles y exportables.

Campos mínimos recomendados:
- `session_id`
- `fecha`
- `codigo_paciente`
- `ejercicio`
- `angulo_minimo_objetivo`
- `angulo_maximo_objetivo`
- `angulo_maximo_alcanzado`
- `repeticiones_realizadas`
- `porcentaje_en_rango`
- `observacion`

Guardar reportes generados en una carpeta ignorada por Git, por ejemplo:

```text
sesiones/
reports/
```

Asegurarse de que `.gitignore` excluya:
- videos,
- capturas pesadas,
- reportes reales,
- perfiles reales,
- entornos virtuales,
- cachés.

---

## Reglas de seguridad, ética y privacidad

1. Este sistema no reemplaza a un fisioterapeuta.
2. No usar el sistema para diagnosticar enfermedades o lesiones.
3. No guardar datos personales reales en GitHub.
4. No subir videos de pacientes al repositorio.
5. No usar lenguaje clínico definitivo en reportes.
6. Toda prueba con pacientes debe ser supervisada por personal autorizado.
7. Los ejemplos deben usar datos ficticios.

---

## Criterios de terminado

Una tarea se considera terminada cuando:
- El código corre sin errores obvios.
- Existe prueba manual o unitaria.
- No se rompió `python -m freemocap`.
- Se actualizaron README o docs si cambió la forma de uso.
- El cambio respeta la licencia AGPLv3.
- No se añadieron datos sensibles.
- Codex deja un resumen claro de archivos modificados y cómo probar.

---

## Formato esperado de respuesta de Codex

Al finalizar una tarea, responder siempre con:

1. Resumen breve de lo realizado.
2. Archivos modificados.
3. Comandos ejecutados.
4. Resultado de pruebas.
5. Pendientes o riesgos.
6. Siguiente paso recomendado.

---

## Primeras tareas sugeridas para Codex

Después de leer este archivo, trabajar en este orden:

1. Revisar la estructura del repositorio.
2. Verificar que FreeMoCap ejecuta.
3. Crear `assets/` si no existe.
4. Revisar y mejorar `README.md` con identidad PUCE, Fe y Alegría y créditos.
5. Crear `freemocap/puce_mocap/angle_utils.py`.
6. Crear pruebas unitarias para `calcular_angulo`.
7. Crear base de `exercise_analyzer.py`.
8. Crear base de `rehab_profiles.py`.
9. Crear base de `gait_analyzer.py`.
10. Documentar cómo ejecutar cada avance.

---

## No hacer

- No eliminar archivos originales importantes de FreeMoCap.
- No reemplazar todo el proyecto por un script aislado.
- No subir `venv/`.
- No subir videos de pacientes.
- No subir reportes reales.
- No cambiar la licencia.
- No prometer precisión clínica.
- No implementar muchas funcionalidades incompletas al mismo tiempo.
- No mezclar lógica de cálculo, interfaz y reportes en un solo archivo enorme.
