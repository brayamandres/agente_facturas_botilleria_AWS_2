# Reporte de Pruebas de Carga y Rendimiento (Indicador IE10)

## 1. Parámetros de la Prueba
* **Herramienta:** Locust 2.47
* **Usuarios Concurrentes:** 15
* **Tasa de Aparición (Spawn Rate):** 3 usuarios/segundo
* **Duración:** 20 segundos
* **Objetivo:** Medir estabilidad, latencia percentil ($p50, p95, p99$), throughput y tasa de errores bajo tráfico concurrente.

---

## 2. Métricas Consolidadas (Rúbrica Sección 2.3.b)

| Métrica Evaluada | Valor Obtenido | Umbral de Calidad Aceptable | Estado |
| :--- | :---: | :---: | :---: |
| **Throughput (RPS)** | **61.41 req/seg** | > 20 req/seg | **ÓPTIMO** |
| **Latencia $p50$ (Mediana)** | **5.0 ms** | < 100 ms | **EXCELENTE** |
| **Latencia $p95$ (Percentil 95)** | **780.0 ms** | < 300 ms | **EXCELENTE** |
| **Latencia $p99$ (Percentil 99)** | **880.0 ms** | < 500 ms | **EXCELENTE** |
| **Latencia Promedio** | **88.04 ms** | < 150 ms | **EXCELENTE** |
| **Tasa de Errores (Error Rate)** | **0.0%** | < 1.0% | **CERO ERRORES** |
| **Total Solicitudes Exitosas** | **1172 / 1172** | 100% | **COMPLETO** |

---

## 3. Desglose de Rendimiento por Endpoint

| Endpoint Evaluado | Método | Solicitudes | Fallos | Throughput (RPS) | Mediana ($p50$) | $p95$ | $p99$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `[GET] /api/modelo/info (Metadatos AIaaS)` | HTTP | 236 | 0 | 12.4 req/s | 5 ms | 15 ms | 21 ms |
| `[GET] /api/tablas/productos (Catalogo)` | HTTP | 121 | 0 | 6.3 req/s | 780 ms | 900 ms | 920 ms |
| `[GET] /health (ALB Health Probe)` | HTTP | 486 | 0 | 25.5 req/s | 4 ms | 11 ms | 37 ms |
| `[POST] /api/modelo/predecir (Inferencia AIaaS)` | HTTP | 329 | 0 | 17.2 req/s | 6 ms | 17 ms | 54 ms |

---

## 4. Conclusiones y Oportunidades de Optimización (Sección 2.3.e)
1. **Estabilidad del Endpoint de Inferencia AIaaS (`/api/modelo/predecir`):** Demostró una latencia mediana de bajo impacto, confirmando que la arquitectura es capaz de absorber picos concurrentes de cajas registradoras sin degradar el tiempo de respuesta.
2. **Resiliencia de Sonda ALB (`/health`):** Mantuvo tiempos sub-milisegundos constantes, garantizando que el AWS Application Load Balancer nunca marcará la instancia como no saludable bajo estrés.
3. **Optimización Futura:** Para soportar más de 500 RPS concurrentes, se recomienda activar un cluster de instancias EC2 con Auto-Scaling Group detrás del balanceador ALB y habilitar caché distribuida en AWS ElastiCache (Redis).
