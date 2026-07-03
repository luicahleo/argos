"""
ARGOS - API Client for ICARUS.API
Handles communication with the .NET backend for embedding storage and retrieval
"""

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Dict, Any
from ARGOS.logger import logger, log_error

# Configuration
ICARUS_API_URL = os.environ.get('ICARUS_API_URL', 'http://localhost:5090')
ICARUS_SERVICE_KEY = os.environ.get('ICARUS_SERVICE_KEY', '')
API_TIMEOUT = 30  # seconds


class IcarusApiUnavailableError(Exception):
    """
    Backend no disponible (timeout, conexion rechazada, o 5xx tras agotar reintentos).
    Se distingue explicitamente de una respuesta 200 con lista vacia, que significa "sin
    trabajadores registrados" y no es un error.
    """
    pass


class IcarusApiClient:
    """Client for communicating with ICARUS.API"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or ICARUS_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Service-Key': ICARUS_SERVICE_KEY
        })

        # Reintentos con backoff exponencial (0.5s, 1s, 2s) ante timeouts/errores de conexion y
        # respuestas 5xx del backend. No reintenta 4xx (son errores del cliente, no del backend).
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=frozenset(['GET', 'HEAD'])
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        logger.info(f"IcarusApiClient initialized with base URL: {self.base_url}")

    def get_embeddings_by_cliente(self, cliente_id: int) -> List[Dict[str, Any]]:
        """
        Get all facial embeddings for a client

        Args:
            cliente_id: Client ID

        Returns:
            List of embeddings with worker IDs. Puede ser una lista vacia si el cliente no tiene
            trabajadores registrados (respuesta 200 valida) — eso NO es un error.

        Raises:
            IcarusApiUnavailableError: si el backend no respondio tras agotar los reintentos
            (timeout, conexion rechazada, o 5xx persistente). El llamador debe distinguir esto
            de una lista vacia legitima.
        """
        endpoint = f"{self.base_url}/api/imca/biometria/embeddings/{cliente_id}"

        try:
            logger.info(f"Fetching embeddings for ClienteId: {cliente_id}")
            response = self.session.get(endpoint, timeout=API_TIMEOUT)
            response.raise_for_status()

            result = response.json()
            count = len(result) if isinstance(result, list) else 0
            logger.info(f"Retrieved {count} embeddings for ClienteId: {cliente_id}")
            return result

        except requests.exceptions.RequestException as e:
            log_error("get_embeddings_by_cliente", e, f"ClienteId: {cliente_id}")
            raise IcarusApiUnavailableError(
                f"ICARUS.API no disponible al obtener embeddings de ClienteId {cliente_id}: {e}"
            ) from e

    def health_check(self) -> bool:
        """Check if ICARUS.API is available"""
        try:
            # Try a simple GET to verify API is responding
            # Using HEAD or GET to base URL to avoid triggering validation errors
            response = self.session.get(f"{self.base_url}/api/imca/ping", timeout=5)
            # Any response means API is up (even 404 for non-existent endpoint)
            return response.status_code in [200, 404]
        except:
            return False


# Global client instance
api_client = IcarusApiClient()
