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

> **Actualizado con datos reales del agenteVPS (docs 50 y 52, 2026-09-30).**

## Decisiones arquitectónicas

- Trajano-Icarus custodia las plantillas faciales cifradas; ARGOS **solo procesa**
  cada petición, sin base de datos, perfiles persistentes ni caché biométrica
  entre peticiones.
- El nuevo flujo **no consulta ICARUS legacy** ni usa `ARGOS/api_client.py`.
- Se preserva `/api/verify` y el flujo KYC de Caserito sin cambios.
- Autenticación interna por API key compartida (`CONTROL_ACCESO_API_KEY` en
  `.env.production` del contenedor; `Authorization: Bearer <key>` desde Trajano).
- Prefijo de ruta: `/api/v2/control-acceso`.

## Estado real del entorno (doc 50)

| Aspecto | Valor observado |
|---|---|
| Imagen desplegada | `argos:latest` 2026-08-06 (`sha256:12f6b1e7dcf8…`); misma batería doc 34. |
| Modelo/métrica/umbral | `ArcFace` / `cosine` / `0.68`. |
| Detector | `opencv` (OpenCV 4.14.0.94). |
| Embedding | 512 dimensiones. |
| Hardware | CPU; sin GPU. |
| Workers Gunicorn | 2. |
| Memoria | Sin límite actual; se recomienda `mem_limit=2g` al redeployar v2. |
| Red | `trajano-shared-network`; puerto 5000 no publicado. |
| Carga `/api/verify` | 20 llamadas totales (baterías agosto), cero producción desde entonces. |
| PAD | Ningún modelo instalado; DeepFace FASNet (`anti_spoofing=True`) requiere pre-descargar pesos en la imagen. |
| API key | `CONTROL_ACCESO_API_KEY` ya añadida a `.env.production` (chmod 600); valor por canal seguro. |
| Memoria | `mem_limit=2g` confirmado; aplica en `deploy-production.sh` (`--memory 2g`). |
| Logs | `logrotate` configurado en VPS; `--log-opt max-size=10m --log-opt max-file=5` pendiente en `deploy-production.sh`. |
| Health check | Se recomienda quitar el chequeo `icarus_api` legacy de `/health` en v2. |
| Staging | No existe; usar contenedor candidato aislado `argos-v2-candidate` antes del swap. |
| Pesos PAD | Host de build (la VPS) tiene internet; pre-hornear durante el build del Dockerfile. |

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

## Ajustes operativos para el redeploy de v2

- Fijar `CONTROL_ACCESO_API_KEY` en `.env.production`.
- Fijar `mem_limit=2g` en el compose del servicio `argos`.
- Añadir `logging.options.max-size`/`max-file` al compose y logrotate para
  `logs/`.
- Añadir `%D` al formato de log de Gunicorn para medir latencia.
- Pre-descargar los pesos de FASNet en el `Dockerfile` si se habilita PAD.

## Próximos pasos

1. Leer el spec completo y el plan ejecutable en Trajano-Icarus.
2. Responder las preguntas de seguimiento del agenteLocal en el documento 51 de
   la carpeta de correspondencia con agenteVPS.
3. Implementar `ARGOS/control_acceso_v2.py` y `ARGOS/tests/test_control_acceso_v2.py`
   siguiendo el plan.
4. Ejecutar `python -m unittest discover -s tests -p 'test_*.py' -v` y
   `docker build -t argos:control-acceso-validacion .` antes de integrar.
