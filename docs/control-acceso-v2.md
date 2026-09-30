# Control de acceso — contrato v2

**Fecha:** 2026-09-30  
**Repo de referencia:** Trajano-Icarus,
`docs/superpowers/specs/2026-09-30-control-acceso-argos-contrato-v2-design.md` y
`docs/superpowers/plans/2026-09-30-control-acceso-argos-contrato-v2.md`.

## Alcance

Este documento es el punto de entrada en el repo ARGOS para implementar el
contrato v2 que consumirá Trajano-Icarus (módulo Control de acceso). El spec
completo y el plan ejecutable viven en Trajano-Icarus; este archivo solo resume
las decisiones y enlaza al trabajo detallado.

## Decisiones arquitectónicas

- Trajano-Icarus custodia las plantillas faciales cifradas; ARGOS **solo procesa**
  cada petición, sin base de datos, perfiles persistentes ni caché biométrica
  entre peticiones.
- El nuevo flujo **no consulta ICARUS legacy** ni usa `ARGOS/api_client.py`.
- Se preserva `/api/verify` y el flujo KYC de Caserito sin cambios.
- Autenticación interna por API key compartida (`CONTROL_ACCESO_API_KEY`).
- Prefijo de ruta: `/api/v2/control-acceso`.

## Endpoints

| Método | Ruta | Propósito |
|---|---|---|
| GET | `/api/v2/control-acceso/capacidades` | Anunciar modelo, detector, dimensión, métrica, umbral, PAD y versión de contrato. |
| POST | `/api/v2/control-acceso/extracciones` | Extraer vector de una imagen temporal y evaluar PAD pasivo. |
| POST | `/api/v2/control-acceso/identificaciones` | Identificar 1:N contra candidatos enviados por Trajano-Icarus. |

## Formato de intercambio

- Imagen: base64, JPEG/PNG, máx. 2 MiB, 1920×1920.
- Vector: array de `float`.
- Referencias de candidatos: GUID string (`trabajador_id`).
- Modelo/formato/version explícitos para detectar incompatibilidad.

## Códigos de negocio facial

- `sin_rostro`
- `varios_rostros`
- `pad_fallido`
- `extraccion_fallida`
- `sin_coincidencia`
- `ambigua`
- `modelo_incompatible`
- `sin_candidatos`

## Privacidad

- No conservar imágenes, vectores ni candidatos entre peticiones.
- No escribir identidades, puntuaciones completas ni motivos biométricos en logs.
- No recibir claves de cifrado de Trajano-Icarus.

## Próximos pasos

1. Leer el spec completo y el plan ejecutable en Trajano-Icarus.
2. Responder las preguntas del agenteLocal en el documento 49 de la carpeta de
   correspondencia con agenteVPS.
3. Implementar `ARGOS/control_acceso_v2.py` y `ARGOS/tests/test_control_acceso_v2.py`
   siguiendo el plan.
4. Ejecutar `python -m unittest discover -s tests -p 'test_*.py' -v` y
   `docker build -t argos:control-acceso-validacion .` antes de integrar.
