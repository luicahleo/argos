"""
ARGOS - Face Recognition API Routes
Routes for facial embedding extraction, verification, and identification
"""

import time
import base64
import numpy as np
from io import BytesIO
from flask import request, jsonify
from PIL import Image
from deepface import DeepFace
from ARGOS import app, MODEL_NAME, DETECTOR_BACKEND, VERIFICATION_THRESHOLD
from ARGOS.logger import logger, log_request, log_response, log_error, log_model_operation
from ARGOS.api_client import api_client, IcarusApiUnavailableError
from ARGOS.decorators import api_route
from functools import lru_cache
from threading import Lock

# ============================================
# Embeddings Cache (5 minute TTL per client)
# ============================================
CACHE_TTL_SECONDS = 300  # 5 minutes
_embeddings_cache = {}  # {cliente_id: {"embeddings": [...], "timestamp": time.time()}}
_cache_lock = Lock()


def get_cached_embeddings(cliente_id: int):
    """Get embeddings from cache if valid, else fetch from API."""
    with _cache_lock:
        if cliente_id in _embeddings_cache:
            cached = _embeddings_cache[cliente_id]
            if time.time() - cached["timestamp"] < CACHE_TTL_SECONDS:
                logger.info(f"Cache HIT for ClienteId: {cliente_id}")
                return cached["embeddings"]
            else:
                logger.info(f"Cache EXPIRED for ClienteId: {cliente_id}")
                del _embeddings_cache[cliente_id]
    
    # Cache miss - fetch from API
    logger.info(f"Cache MISS for ClienteId: {cliente_id}")
    embeddings = api_client.get_embeddings_by_cliente(cliente_id)
    
    if embeddings:
        with _cache_lock:
            _embeddings_cache[cliente_id] = {
                "embeddings": embeddings,
                "timestamp": time.time()
            }
    
    return embeddings


def invalidate_cache(cliente_id: int = None):
    """Invalidate cache for a client or all clients."""
    with _cache_lock:
        if cliente_id:
            _embeddings_cache.pop(cliente_id, None)
            logger.info(f"Cache invalidated for ClienteId: {cliente_id}")
        else:
            _embeddings_cache.clear()
            logger.info("Cache cleared for all clients")


def decode_base64_image(base64_string: str) -> np.ndarray:
    """Decode a base64 image string to numpy array."""
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    
    image_bytes = base64.b64decode(base64_string)
    image = Image.open(BytesIO(image_bytes))
    
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    return np.array(image)


def calculate_cosine_distance(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Calculate cosine distance between two embeddings."""
    dot = np.dot(emb1, emb2)
    norm1 = np.linalg.norm(emb1)
    norm2 = np.linalg.norm(emb2)
    return 1 - (dot / (norm1 * norm2))


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    client_ip = request.remote_addr
    log_request("/health", client_ip=client_ip)
    
    # Check ICARUS.API connectivity
    api_available = api_client.health_check()
    
    response = {
        "status": "healthy",
        "service": "ARGOS Face Recognition",
        "model": MODEL_NAME,
        "version": "1.0.0",
        "icarus_api": "connected" if api_available else "disconnected"
    }
    
    log_response("/health", True, f"API: {'connected' if api_available else 'disconnected'}")
    return jsonify(response)


@app.route("/api/extract-embedding", methods=["POST"])
@api_route(required_fields=["image"], error_extra={"face_detected": False})
def extract_embedding(data, start_time):
    """
    Extract facial embedding from an image.

    Request: { "image": "base64_encoded_image" }
    Response: { "success": true, "embedding": [...], "face_detected": true }
    """
    image_array = decode_base64_image(data["image"])
    logger.debug(f"Image decoded: shape={image_array.shape}")

    log_model_operation("represent", MODEL_NAME)
    embeddings = DeepFace.represent(
        img_path=image_array,
        model_name=MODEL_NAME,
        detector_backend=DETECTOR_BACKEND,
        enforce_detection=True
    )

    if not embeddings:
        log_response("/api/extract-embedding", False, "No face detected")
        return jsonify({"success": False, "error": "No face detected", "face_detected": False}), 400

    embedding = embeddings[0]["embedding"]
    duration_ms = (time.time() - start_time) * 1000

    log_response("/api/extract-embedding", True, f"Embedding size: {len(embedding)}", duration_ms)

    return jsonify({
        "success": True,
        "embedding": embedding,
        "face_detected": True,
        "embedding_size": len(embedding)
    })


@app.route("/api/verify", methods=["POST"])
@api_route(required_fields=["image1", "image2"])
def verify_faces(data, start_time):
    """
    Verify if two faces belong to the same person.

    Request: { "image1": "base64_1", "image2": "base64_2" }
    Response: { "success": true, "verified": true/false, "similarity_percent": float }
    """
    img1 = decode_base64_image(data["image1"])
    img2 = decode_base64_image(data["image2"])

    log_model_operation("verify", MODEL_NAME)
    result = DeepFace.verify(
        img1_path=img1,
        img2_path=img2,
        model_name=MODEL_NAME,
        distance_metric="cosine",
        detector_backend=DETECTOR_BACKEND,
        enforce_detection=True
    )

    distance = result["distance"]
    verified = distance <= VERIFICATION_THRESHOLD
    similarity = max(0, (1 - distance) * 100)
    duration_ms = (time.time() - start_time) * 1000

    log_response("/api/verify", True, f"Verified: {verified}, Similarity: {similarity:.2f}%", duration_ms)

    return jsonify({
        "success": True,
        "verified": verified,
        "distance": distance,
        "threshold": VERIFICATION_THRESHOLD,
        "similarity_percent": round(similarity, 2)
    })


@app.route("/api/identify", methods=["POST"])
@api_route(required_fields=["image"], error_extra={"identified": False})
def identify_face(data, start_time):
    """
    1:N Identification - Find matching face from stored embeddings.

    Option 1 - With embeddings in request:
    {
        "image": "base64_encoded_image",
        "embeddings": [{"id": "worker_1", "embedding": [...]}],
        "threshold": 0.68 (optional)
    }

    Option 2 - Fetch embeddings from ICARUS.API:
    {
        "image": "base64_encoded_image",
        "cliente_id": 1,
        "threshold": 0.68 (optional)
    }

    Response: {
        "success": true,
        "identified": true/false,
        "match": { "id": "worker_1", "similarity_percent": 75.0 }
    }
    """
    threshold = data.get("threshold", VERIFICATION_THRESHOLD)

    # Get embeddings: either from request or from ICARUS.API
    embeddings_list = data.get("embeddings")

    if not embeddings_list and "cliente_id" in data:
        cliente_id = data["cliente_id"]
        logger.info(f"Fetching embeddings for ClienteId: {cliente_id}")

        try:
            embeddings_list = get_cached_embeddings(cliente_id)  # Use cache
        except IcarusApiUnavailableError as e:
            # Distinto de "0 trabajadores registrados": aqui el backend no respondio tras
            # agotar los reintentos, no que el cliente no tenga trabajadores.
            log_response("/api/identify", False, f"ICARUS.API no disponible: {e}")
            return jsonify({
                "success": False,
                "error": "El backend ICARUS.API no esta disponible. Intente nuevamente.",
                "identified": False
            }), 503

        if not embeddings_list:
            log_response("/api/identify", False, f"No embeddings found for ClienteId: {cliente_id}")
            return jsonify({
                "success": False,
                "error": f"No registered workers found for cliente_id: {cliente_id}",
                "identified": False
            }), 404

    if not embeddings_list:
        log_response("/api/identify", False, "No embeddings provided")
        return jsonify({
            "success": False,
            "error": "Either 'embeddings' or 'cliente_id' must be provided"
        }), 400

    logger.info(f"Comparing against {len(embeddings_list)} stored embeddings")

    # Decode image and extract embedding
    image_array = decode_base64_image(data["image"])

    log_model_operation("represent", MODEL_NAME)
    probe_embeddings = DeepFace.represent(
        img_path=image_array,
        model_name=MODEL_NAME,
        detector_backend=DETECTOR_BACKEND,
        enforce_detection=True
    )

    if not probe_embeddings:
        log_response("/api/identify", False, "No face detected in probe image")
        return jsonify({
            "success": False,
            "error": "No face detected in probe image",
            "identified": False
        }), 400

    probe_embedding = np.array(probe_embeddings[0]["embedding"])

    # Find best match
    best_match = None
    best_distance = float("inf")
    all_matches = []

    for candidate in embeddings_list:
        candidate_embedding = np.array(candidate.get("embedding") or candidate.get("embeddingFacial"))

        if candidate_embedding is None or len(candidate_embedding) == 0:
            continue

        distance = calculate_cosine_distance(probe_embedding, candidate_embedding)
        similarity = max(0, (1 - distance) * 100)

        candidate_id = candidate.get("id") or candidate.get("trabajadorAccesoId")
        all_matches.append({
            "id": candidate_id,
            "distance": round(distance, 4),
            "similarity_percent": round(similarity, 2)
        })

        if distance < best_distance:
            best_distance = distance
            best_match = candidate

    # Sort by similarity descending
    all_matches.sort(key=lambda x: x["similarity_percent"], reverse=True)

    identified = bool(best_distance <= threshold)  # Convert numpy.bool_ to Python bool
    similarity = float(max(0, (1 - best_distance) * 100))  # Convert to Python float
    duration_ms = (time.time() - start_time) * 1000

    response = {
        "success": True,
        "identified": identified,
        "threshold": threshold,
        "candidates_count": len(embeddings_list)
    }

    if best_match:
        match_id = best_match.get("id") or best_match.get("trabajadorAccesoId")
        trabajador_id = best_match.get("trabajadorId")

        response["match"] = {
            "id": int(match_id) if match_id is not None else None,
            "trabajador_id": int(trabajador_id) if trabajador_id is not None else None,
            "distance": float(round(best_distance, 4)),
            "similarity_percent": float(round(similarity, 2))
        }

        # Include top 3 matches for debugging
        response["top_matches"] = all_matches[:3]

    log_response("/api/identify", identified,
                f"Identified: {identified}, Best similarity: {similarity:.2f}%", duration_ms)

    return jsonify(response)


@app.route("/api/compare-embeddings", methods=["POST"])
@api_route(required_fields=["embedding1", "embedding2"])
def compare_embeddings(data, start_time):
    """
    Compare two pre-computed embeddings directly.

    Request: { "embedding1": [...], "embedding2": [...] }
    Response: { "success": true, "verified": true/false, "similarity_percent": float }
    """
    threshold = data.get("threshold", VERIFICATION_THRESHOLD)

    emb1 = np.array(data["embedding1"])
    emb2 = np.array(data["embedding2"])

    distance = calculate_cosine_distance(emb1, emb2)
    verified = bool(distance <= threshold)  # Convert numpy.bool_ to Python bool
    similarity = float(max(0, (1 - distance) * 100))  # Convert to Python float

    duration_ms = (time.time() - start_time) * 1000
    log_response("/api/compare-embeddings", True, f"Similarity: {similarity:.2f}%", duration_ms)

    return jsonify({
        "success": True,
        "verified": verified,
        "distance": float(round(distance, 4)),
        "threshold": float(threshold),
        "similarity_percent": float(round(similarity, 2))
    })
