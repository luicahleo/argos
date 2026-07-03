# ARGOS - Face Recognition Microservice

**Versión:** 1.0.0  
**Puerto:** 5000  
**Tecnología:** Python 3.9 + Flask + DeepFace (ArcFace)  
**Precisión:** 99.8%

---

## 📋 Descripción

ARGOS es el microservicio de reconocimiento facial del ecosistema ICARUS. Proporciona identificación biométrica de alta precisión utilizando el modelo **ArcFace** a través de la librería **DeepFace**.

**Nombre:** ARGOS (referencia al gigante de 100 ojos de la mitología griega)

---

## 🏗️ Arquitectura

```
IMCA (Android) → ARGOS (Python) → ICARUS.API (.NET)
                     ↓
              DeepFace/ArcFace
                     ↓
              Embedding (512 floats)
```

---

## 📂 Estructura del Proyecto

```
ARGOS/
├── ARGOS/
│   ├── __init__.py        # Configuración Flask + DeepFace
│   ├── views.py           # Endpoints REST API
│   ├── logger.py          # Sistema de logging
│   ├── static/            # Archivos estáticos
│   └── templates/         # Templates HTML (no usado)
├── logs/                   # Logs de la aplicación
├── runserver.py           # Punto de entrada
├── requirements.txt       # Dependencias Python
├── .env.example           # Configuración de ejemplo
└── ARGOS.pyproj           # Proyecto Visual Studio
```

---

## 🚀 Instalación

### Requisitos
- Python 3.9+
- Visual Studio 2022 (opcional)
- 4GB RAM mínimo (modelo ArcFace)

### Pasos

1. **Crear entorno virtual**
   ```bash
   cd MICROSERVICIOS\ARGOS
   python -m venv env
   ```

2. **Activar entorno**
   ```bash
   .\env\Scripts\activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar**
   ```bash
   python runserver.py
   ```

---

## 🔌 Endpoints API

### Health Check

```http
GET /health
```

**Response:**
```json
{
    "status": "healthy",
    "service": "ARGOS Face Recognition",
    "model": "ArcFace",
    "version": "1.0.0"
}
```

---

### Extraer Embedding

```http
POST /api/extract-embedding
Content-Type: application/json

{
    "image": "base64_encoded_image"
}
```

**Response:**
```json
{
    "success": true,
    "embedding": [0.0324, -0.0812, ...],  // 512 floats
    "face_detected": true,
    "embedding_size": 512
}
```

---

### Verificar Rostros (1:1)

```http
POST /api/verify
Content-Type: application/json

{
    "image1": "base64_image_1",
    "image2": "base64_image_2"
}
```

**Response:**
```json
{
    "success": true,
    "verified": true,
    "distance": 0.32,
    "threshold": 0.68,
    "similarity_percent": 68.0
}
```

---

### Identificación 1:N

```http
POST /api/identify
Content-Type: application/json

{
    "image": "base64_probe_image",
    "embeddings": [
        {"id": "worker_1", "embedding": [...]},
        {"id": "worker_2", "embedding": [...]}
    ],
    "threshold": 0.68
}
```

**Response:**
```json
{
    "success": true,
    "identified": true,
    "probe_embedding": [...],
    "match": {
        "id": "worker_1",
        "distance": 0.25,
        "similarity_percent": 75.0
    }
}
```

---

### Comparar Embeddings

```http
POST /api/compare-embeddings
Content-Type: application/json

{
    "embedding1": [0.0324, ...],
    "embedding2": [-0.0812, ...],
    "threshold": 0.68
}
```

**Response:**
```json
{
    "success": true,
    "verified": true,
    "distance": 0.15,
    "similarity_percent": 85.0
}
```

---

## ⚙️ Configuración

### Variables de Entorno

| Variable | Valor Default | Descripción |
|----------|---------------|-------------|
| `PORT` | 5000 | Puerto del servidor |
| `DEBUG` | false | Modo debug |
| `SERVER_HOST` | 0.0.0.0 | Host de escucha |
| `ICARUS_API_URL` | http://localhost:5090 | URL de ICARUS.API |

### Modelo DeepFace

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `MODEL_NAME` | ArcFace | Modelo de reconocimiento |
| `DISTANCE_METRIC` | cosine | Métrica de distancia |
| `DETECTOR_BACKEND` | opencv | Detector de rostros |
| `VERIFICATION_THRESHOLD` | 0.68 | Umbral de verificación |

---

## 📊 Modelo ArcFace

### Características

| Propiedad | Valor |
|-----------|-------|
| **Precisión** | 99.8% (LFW) |
| **Tamaño embedding** | 512 floats |
| **Tamaño modelo** | ~137MB |
| **Tiempo inferencia** | ~1-2s |

### Umbral de Verificación

```
Distancia Coseno:
  0.0 = Idénticos
  0.68 = Umbral default (32% similitud mínima)
  1.0 = Completamente diferentes
  
Similitud = (1 - distancia) * 100
```

---

## 📝 Logging

Los logs se guardan en `logs/argos.log` con rotación automática.

### Formato

```
[2026-01-03 19:30:45] INFO - views.health_check - Health check requested
[2026-01-03 19:30:46] INFO - views.extract_embedding - Extracting embedding from image
[2026-01-03 19:30:48] INFO - views.extract_embedding - Face detected, embedding size: 512
```

### Niveles

- `DEBUG`: Información detallada para debugging
- `INFO`: Operaciones normales
- `WARNING`: Situaciones anómalas
- `ERROR`: Errores que impiden la operación

---

## 🔗 Integración

### Con IMCA (Android)

```csharp
// ArgosService.cs
public async Task<IdentifyResult> IdentifyFaceAsync(byte[] photo, int clienteId)
{
    var request = new { image = Convert.ToBase64String(photo), cliente_id = clienteId };
    var response = await _httpClient.PostAsJsonAsync($"{ArgosUrl}/api/identify", request);
    return await response.Content.ReadFromJsonAsync<IdentifyResult>();
}
```

### Con ICARUS.API (.NET)

ARGOS consulta embeddings vía:
```http
GET http://localhost:5090/api/biometria/embeddings/{clienteId}
```

---

## 🛠️ Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| Modelo no carga | Primera ejecución | Esperar descarga (~137MB) |
| No detecta rostro | Imagen sin rostro | Verificar calidad de imagen |
| Alta latencia | CPU lento | Considerar GPU (CUDA) |
| Error de memoria | RAM insuficiente | Aumentar a 4GB+ |

---

## 📄 Licencia

TRAJANO Software - Uso exclusivo para clientes con licencia activa de ICARUS.
