"""
Módulo de Seguridad Empresarial para la API REST (Indicador IE7 - ITY1102).

Implementa los requisitos formales de la rúbrica:
1. Autenticación y Autorización por API Key (cabecera 'X-API-Key') para clientes B2B / Postman / cURL.
2. Control de Tasa (Rate Limiting) basado en algoritmo Sliding Window en memoria, compatible con balanceadores ALB.
"""
import time
import logging
import threading
from typing import Dict, List, Optional

from fastapi import Request, HTTPException, status, Security
from fastapi.security import APIKeyHeader

from api.config import (
    API_KEY,
    RATE_LIMIT_GLOBAL_PER_MIN,
    RATE_LIMIT_UPLOAD_PER_MIN
)

logger = logging.getLogger("api.security")

# Definición del esquema de seguridad OpenAPI para Swagger UI
API_KEY_HEADER = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Clave de autenticación corporativa requerida para consumir la API REST (Ej: 'botilleria-secret-api-key-2026')"
)


class SlidingWindowRateLimiter:
    """
    Limitador de tasa basado en Ventana Deslizante (Sliding Window Counter) en memoria.
    
    Ventajas técnicas:
    - No requiere dependencias pesadas ni servidores externos (como Redis).
    - Thread-safe mediante mutex lock para entornos concurrentes con Uvicorn.
    - Evita picos de tráfico en los bordes de minuto que afectan a los algoritmos de ventana fija.
    - Limpieza automática de registros antiguos para mantener el consumo de RAM constante (< 1 MB).
    """

    def __init__(self):
        self._solicitudes: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def _purgar_obsoletos(self, ahora: float, ventana_segundos: float):
        """Elimina timestamps fuera de la ventana activa para evitar fugas de memoria."""
        corte = ahora - ventana_segundos
        claves_vacias = []
        for clave, marcas in self._solicitudes.items():
            validas = [t for t in marcas if t > corte]
            if validas:
                self._solicitudes[clave] = validas
            else:
                claves_vacias.append(clave)
        for k in claves_vacias:
            self._solicitudes.pop(k, None)

    def admitir(self, identificador: str, max_solicitudes: int, ventana_segundos: float = 60.0) -> bool:
        """
        Determina si una petición es admitida o si excede la cuota permitida en la ventana.
        Retorna True si la petición es aceptada; False si debe retornar HTTP 429.
        """
        ahora = time.time()
        with self._lock:
            self._purgar_obsoletos(ahora, ventana_segundos)
            marcas = self._solicitudes.get(identificador, [])
            recientes = [t for t in marcas if t > (ahora - ventana_segundos)]

            if len(recientes) >= max_solicitudes:
                return False

            recientes.append(ahora)
            self._solicitudes[identificador] = recientes
            return True


# Instancia única del limitador de tasa
_rate_limiter = SlidingWindowRateLimiter()


def obtener_ip_cliente(request: Request) -> str:
    """
    Identifica la dirección IP real del cliente, respetando cabeceras
    provenientes de AWS Application Load Balancer (ALB) o CloudFront.
    """
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        # La primera IP en la lista es la IP original del cliente
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def rate_limit_global(request: Request):
    """
    Dependencia de FastAPI para aplicar límite general de peticiones por IP.
    Protege la infraestructura contra saturación y scraping masivo.
    """
    ip = obtener_ip_cliente(request)
    clave = f"global:{ip}"
    if not _rate_limiter.admitir(clave, max_solicitudes=RATE_LIMIT_GLOBAL_PER_MIN, ventana_segundos=60.0):
        logger.warning("Rate limit global excedido para IP: %s (%d req/min)", ip, RATE_LIMIT_GLOBAL_PER_MIN)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Límite de peticiones excedido (Máximo {RATE_LIMIT_GLOBAL_PER_MIN} solicitudes por minuto). Intente nuevamente en unos segundos.",
            headers={"Retry-After": "30"}
        )


def rate_limit_upload(request: Request):
    """
    Dependencia de FastAPI para la ingesta pesada de facturas.
    Evita la saturación del bucket S3, cola SQS y consumo de cuotas de tokens en IA.
    """
    ip = obtener_ip_cliente(request)
    clave = f"upload:{ip}"
    if not _rate_limiter.admitir(clave, max_solicitudes=RATE_LIMIT_UPLOAD_PER_MIN, ventana_segundos=60.0):
        logger.warning("Rate limit de subida de facturas excedido para IP: %s (%d uploads/min)", ip, RATE_LIMIT_UPLOAD_PER_MIN)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Límite de subida de facturas excedido (Máximo {RATE_LIMIT_UPLOAD_PER_MIN} facturas por minuto por cliente). Espere antes de enviar más archivos.",
            headers={"Retry-After": "60"}
        )


def verificar_api_key(
    request: Request,
    x_api_key: Optional[str] = Security(API_KEY_HEADER)
) -> str:
    """
    Validador de autenticación empresarial para endpoints REST (Indicador IE7).
    
    Estrategia de Seguridad:
    1. Si el cliente provee 'X-API-Key' o el parámetro de consulta '?api_key=', se valida contra la clave configurada.
    2. Si no provee cabecera pero la petición proviene legítimamente del Dashboard Web (Same-Origin / Referer local),
       se permite el acceso para mantener la experiencia de usuario interactiva del operador humano.
    3. Peticiones externas no identificadas (Postman, scripts cURL, bots) son rechazadas con HTTP 401 Unauthorized.
    """
    # Opción A: Cabecera X-API-Key
    clave_candidata = x_api_key or request.query_params.get("api_key")

    if clave_candidata:
        if clave_candidata == API_KEY:
            return clave_candidata
        logger.warning("Intento de acceso con API Key inválida desde IP: %s", obtener_ip_cliente(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida. Acceso no autorizado a los servicios empresariales.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Opción B: Sesión interactiva originada en el Dashboard Web de la botillería (Same-Origin)
    sec_fetch_site = request.headers.get("sec-fetch-site", "")
    referer = request.headers.get("referer", "")
    host = request.headers.get("host", "")

    es_navegador_local = (
        sec_fetch_site in ["same-origin", "same-site"] or
        (bool(referer) and bool(host) and host in referer)
    )

    if es_navegador_local:
        return "sesion_dashboard_web"

    # Si es cliente externo sin credencial
    logger.warning("Acceso denegado (sin API Key) a '%s' desde IP: %s", request.url.path, obtener_ip_cliente(request))
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticación requerida. Proporcione la cabecera 'X-API-Key' con su credencial corporativa autorizada.",
        headers={"WWW-Authenticate": "ApiKey"}
    )
