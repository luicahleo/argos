# ARGOS — instrucciones para agentes

- Preservar datos sensibles: nunca registrar imágenes, embeddings, credenciales
  ni contenido biométrico.
- Un solo desarrollador: no hay pull requests. `develop` es la rama de trabajo;
  commit y push directos tras verificar.
- Nunca fusionar ni hacer push a `master` sin pedido explícito del usuario.
- `master` representa producción; desplegar únicamente mediante ejecución manual
  confirmada del workflow `Deploy ARGOS to Production` y con CI verde.
- Antes de integrar, ejecutar las pruebas y construir la imagen Docker.
