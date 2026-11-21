"""
Suite Oficial de Pruebas Automatizadas - Evaluación Parcial N°3 (Indicador IE10).

Cumple estrictamente con los requerimientos de la pauta de evaluación:
- Mínimo 10 casos de prueba (5 pruebas unitarias y 5 pruebas de integración).
- Cobertura de componentes distribuidos, seguridad, lógica de negocio y endpoints de IA.
- Ejecución automatizada con Pytest.
"""
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from shared.finanzas import validar_finanzas
from worker.src.tools.reasoning_tools import (
    evaluar_variacion_costo,
    validar_respuesta_homologacion
)
from api.security import SlidingWindowRateLimiter
from api.main import app, _deserializar_decimales

client = TestClient(app)
API_KEY_VALIDA = "botilleria-secret-api-key-2026"
HEADERS_AUTH = {"X-API-Key": API_KEY_VALIDA}


# ============================================================================
# PARTE I: PRUEBAS UNITARIAS (5 Casos de Prueba - Lógica Aislada)
# ============================================================================

def test_01_unitario_validacion_aritmética_factura_exitosa():
    """
    Caso 1 (Unitario): Validación de consistencia fiscal de factura chilena.
    Verifica que la ecuación Neto + IVA + Impuestos Adicionales = Total sea exacta.
    """
    datos_factura = {
        "proveedor": "COMPAÑIA CERVECERIAS UNIDAS S.A.",
        "rut_proveedor": "96.492.000-K",
        "fecha_emision": "2026-10-15",
        "moneda": "CLP",
        "monto_neto": 100000,
        "monto_iva": 19000,
        "monto_exento": 0,
        "impuestos_adicionales": [],
        "total_factura": 119000
    }
    resultado = validar_finanzas(datos_factura)
    assert resultado["estado_validacion"] == "VALIDADO"
    assert len(resultado["motivos_revision"]) == 0
    assert resultado["total_factura"] == Decimal("119000")


def test_02_unitario_validacion_aritmética_factura_con_descuadre():
    """
    Caso 2 (Unitario): Detección de descuadre aritmético en montos de factura.
    Verifica que si la suma no coincide con el total impreso, se marque para revisión (HITL).
    """
    datos_erroneos = {
        "proveedor": "DISTRIBUIDORA CENTRAL",
        "rut_proveedor": "76.123.456-7",
        "fecha_emision": "2026-10-15",
        "moneda": "CLP",
        "monto_neto": 100000,
        "monto_iva": 19000,
        "monto_exento": 0,
        "impuestos_adicionales": [],
        "total_factura": 150000  # Total erróneo (esperado 119000)
    }
    resultado = validar_finanzas(datos_erroneos)
    assert resultado["estado_validacion"] == "REQUIERE_REVISION"
    codigos_error = [m["codigo"] for m in resultado["motivos_revision"]]
    assert "TOTALES_NO_COINCIDEN" in codigos_error


def test_03_unitario_alerta_variacion_costo_superior_15_porciento():
    """
    Caso 3 (Unitario): Alerta de variación de costos superior al 15%.
    Verifica que incrementos desmedidos en el precio de compra del proveedor activen alertas de margen.
    """
    costo_anterior = 5000.0
    costo_nuevo_subio_20 = 6000.0  # +20% de incremento
    
    alerta_costo = evaluar_variacion_costo.invoke({
        "costo_factura": costo_nuevo_subio_20,
        "costo_actual": costo_anterior,
        "umbral_alerta": 0.15
    })
    
    assert alerta_costo["alerta"] is True
    assert alerta_costo["variacion_porcentual"] == 20.0
    assert "Alerta de aumento de costo" in alerta_costo["mensaje"]


def test_04_unitario_normalizacion_y_calibracion_homologacion_pydantic():
    """
    Caso 4 (Unitario): Validación de esquema Pydantic para decisiones del LLM.
    Verifica que respuestas malformadas o con confianza fuera de rango [0.0, 1.0] sean corregidas.
    """
    candidatos = [{"sku": "SKU-CERV-CORONA", "nombre": "Cerveza Corona 330ml"}]
    
    # Decisión con confianza distorsionada (> 1.0) y SKU nulo
    decision_bruta = {
        "sku_seleccionado": "null",
        "confianza": 1.5,
        "justificacion": "Glosa no concluyente"
    }
    
    validada = validar_respuesta_homologacion(decision_bruta, candidatos=candidatos)
    assert validada["sku_seleccionado"] is None
    assert validada["confianza"] == 1.0  # Ajustado al rango máximo permitido
    assert validada["requiere_revision"] is True


def test_05_unitario_limitador_sliding_window_en_memoria():
    """
    Caso 5 (Unitario): Funcionamiento del algoritmo Sliding Window Rate Limiter.
    Verifica que el limitador admita la cuota exacta y bloquee peticiones subsiguientes.
    """
    limiter = SlidingWindowRateLimiter()
    ip_test = "192.168.1.100"
    cuota_maxima = 3
    
    # Las primeras 3 deben ser admitidas
    assert limiter.admitir(ip_test, max_solicitudes=cuota_maxima, ventana_segundos=60.0) is True
    assert limiter.admitir(ip_test, max_solicitudes=cuota_maxima, ventana_segundos=60.0) is True
    assert limiter.admitir(ip_test, max_solicitudes=cuota_maxima, ventana_segundos=60.0) is True
    
    # La 4ta petición en la misma ventana debe ser rechazada
    assert limiter.admitir(ip_test, max_solicitudes=cuota_maxima, ventana_segundos=60.0) is False


# ============================================================================
# PARTE II: PRUEBAS DE INTEGRACIÓN (5 Casos de Prueba - APIs y Componentes)
# ============================================================================

def test_06_integracion_health_check_load_balancer():
    """
    Caso 6 (Integración): Sonda de salud para AWS Application Load Balancer.
    Verifica que /health responda HTTP 200 sin exigir autenticación (acceso público para el ALB).
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "api-botilleria"


def test_07_integracion_autenticacion_api_key_rechazo_401():
    """
    Caso 7 (Integración): Seguridad Perimetral de API REST (Indicador IE7).
    Verifica que peticiones externas sin cabecera X-API-Key sean rechazadas con HTTP 401 Unauthorized.
    """
    response = client.get("/api/tablas/productos")
    assert response.status_code == 401
    assert "Autenticación requerida" in response.json()["detail"]


def test_08_integracion_rate_limiting_excedido_retorna_429():
    """
    Caso 8 (Integración): Control de tasa y respuesta HTTP 429 Too Many Requests (IE7).
    Verifica que al saturar la cuota de la API se emita código 429 y cabecera 'Retry-After'.
    """
    import api.security as sec
    # Aislamos el test configurando una cuota pequeña
    sec._rate_limiter._solicitudes.clear()
    sec.RATE_LIMIT_GLOBAL_PER_MIN = 2
    
    # Peticiones permitidas
    r1 = client.get("/api/tablas/productos", headers=HEADERS_AUTH)
    r2 = client.get("/api/tablas/productos", headers=HEADERS_AUTH)
    assert r1.status_code == 200
    assert r2.status_code == 200
    
    # Petición 3 excede el límite
    r3 = client.get("/api/tablas/productos", headers=HEADERS_AUTH)
    assert r3.status_code == 429
    assert "Retry-After" in r3.headers
    assert "Límite de peticiones excedido" in r3.json()["detail"]
    
    # Restauramos cuota habitual
    sec.RATE_LIMIT_GLOBAL_PER_MIN = 60
    sec._rate_limiter._solicitudes.clear()


def test_09_integracion_endpoint_inferencia_sagemaker_prediccion():
    """
    Caso 9 (Integración): Consumo de Inferencia Cloud AIaaS con Explicabilidad (IE1, IE2, IE4).
    Verifica que POST /api/modelo/predecir clasifique un ítem real y entregue métricas XAI.
    """
    payload = {
        "glosa": "PISCO MISTRAL 35 750CC",
        "proveedor": "COMPAÑIA PISQUERA DE CHILE S.A.",
        "precio_unitario": 5490.0
    }
    response = client.post("/api/modelo/predecir", json=payload, headers=HEADERS_AUTH)
    assert response.status_code == 200
    data = response.json()
    
    assert "Destilados" in data["categoria"]
    assert data["confianza"] >= 0.85
    assert "interpretabilidad" in data
    assert len(data["interpretabilidad"]["palabras_clave_detectadas"]) > 0
    assert "Aprobación automática" in data["interpretabilidad"]["recomendacion_decision"]


def test_10_integracion_metadatos_endpoint_sagemaker_info():
    """
    Caso 10 (Integración): Metadatos del Modelo y Plataforma AIaaS (Indicadores IE4, E6).
    Verifica que GET /api/modelo/info exponga la región, nombre de endpoint y características.
    """
    response = client.get("/api/modelo/info", headers=HEADERS_AUTH)
    assert response.status_code == 200
    data = response.json()
    
    assert data["plataforma"] == "AWS SageMaker Serverless Inference"
    assert data["region"] == "us-east-1"
    assert data["interpretabilidad_soportada"] is True
    assert "IE1" in data["indicadores_evaluacion"]
    assert "E6" in data["indicadores_evaluacion"]
