# ARGOS — instrucciones para agentes

- Preservar datos sensibles: nunca registrar imágenes, embeddings, credenciales
  ni contenido biométrico.
- Integrar cambios mediante pull request en la rama permanente `develop`.
- Nunca fusionar ni hacer push a `master` sin pedido explícito del usuario.
- `master` representa producción; desplegar únicamente mediante ejecución manual
  confirmada del workflow `Deploy ARGOS to Production` y con CI verde.
- Antes de integrar, ejecutar las pruebas y construir la imagen Docker.
