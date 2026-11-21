"""
Script Oficial de Pruebas de Carga y Rendimiento con Locust.
Evaluación Parcial N°3 (Indicador IE10 - ITY1102).

Mide formalmente:
- Latencia en percentiles: p50 (mediana), p95 y p99.
- Throughput (Solicitudes por segundo / RPS).
- Tasa de errores (Error Rate %).
- Capacidad de escalabilidad del microservicio FastAPI y del endpoint AIaaS.
"""
from locust import HttpUser, task, between
import random

API_KEY = "botilleria-secret-api-key-2026"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

PRODUCTOS_MUESTRA = [
    {"glosa": "PISCO MISTRAL 35 750CC", "proveedor": "COMPAÑIA PISQUERA", "precio_unitario": 5490.0},
    {"glosa": "PACK CERVEZA CORONA 330CC X6", "proveedor": "AB INBEV", "precio_unitario": 4890.0},
    {"glosa": "WHISKY JOHNNIE WALKER RED LABEL 750ML", "proveedor": "DIAGEO CHILE", "precio_unitario": 12990.0},
    {"glosa": "VINO CASILLERO DEL DIABLO CARMENERE 750CC", "proveedor": "CONCHA Y TORO", "precio_unitario": 4290.0},
    {"glosa": "BEBIDA COCA COLA ORIGINAL 1.5L RETORNABLE", "proveedor": "EMBONOR S.A.", "precio_unitario": 1490.0}
]


class UsuarioBotilleria(HttpUser):
    """
    Simula el tráfico concurrente de operadores web, sistemas de caja POS
    y sondas del balanceador de carga AWS Application Load Balancer (ALB).
    """
    wait_time = between(0.05, 0.2)  # Tiempo entre solicitudes para generar carga sostenida

    @task(4)
    def test_health_check_alb(self):
        """Sonda de salud de AWS Application Load Balancer (Alta frecuencia)."""
        self.client.get("/health", name="[GET] /health (ALB Health Probe)")

    @task(3)
    def test_inferencia_sagemaker(self):
        """Inferencia Cloud del Modelo de IA (Indicador IE1, IE2, IE4)."""
        muestra = random.choice(PRODUCTOS_MUESTRA)
        self.client.post(
            "/api/modelo/predecir",
            json=muestra,
            headers=HEADERS,
            name="[POST] /api/modelo/predecir (Inferencia AIaaS)"
        )

    @task(2)
    def test_info_modelo(self):
        """Consulta de metadatos de la plataforma AIaaS (Indicador IE4)."""
        self.client.get(
            "/api/modelo/info",
            headers=HEADERS,
            name="[GET] /api/modelo/info (Metadatos AIaaS)"
        )

    @task(1)
    def test_consulta_catalogo(self):
        """Consulta de inventario y tablas."""
        self.client.get(
            "/api/tablas/productos",
            headers=HEADERS,
            name="[GET] /api/tablas/productos (Catalogo)"
        )
