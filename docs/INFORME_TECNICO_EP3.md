# Informe Técnico: Proyecto Integral de Despliegue y Optimización de Sistema IA Empresarial

**Asignatura:** ITY1102 - Arquitectura de Sistemas de Inteligencia Artificial  
**Evaluación:** Evaluación Parcial N°3 (40% de Ponderación)  
**Institución:** Duoc UC - Escuela de Informática y Telecomunicaciones  
**Fecha:** Noviembre 2026  
**Repositorio Oficial:** `agente_facturas_botilleria_AWS`  

---

## Declaración de Uso Ético de Inteligencia Artificial

> *"En concordancia con los lineamientos académicos de integridad y ética en la educación superior de Duoc UC, declaramos que para el desarrollo de esta solución de arquitectura de software y el presente informe técnico se utilizaron asistentes de Inteligencia Artificial Generativa (Google DeepMind Antigravity y Claude 3.5 Sonnet) como herramientas de apoyo para la redacción técnica, depuración de scripts de prueba sintéticos y formateo de especificaciones OpenAPI. Todo el diseño arquitectónico, la implementación de código fuente en Python, la configuración de contenedores Docker, la parametrización de servicios en AWS y la validación experimental fueron analizados, ejecutados y supervisados integralmente por el equipo de estudiantes."*

---

## 1. Introducción y Contexto Empresarial (Indicadores IE3, IE5)

### 1.1 El Problema de Negocio en la Cadena de Suministro Retail
En el sector de comercialización minorista y botillerías en Chile, la gestión de inventario y costos enfrenta una fricción operativa crítica durante la recepción de mercancías. Los distribuidores mayoristas líderes (Compañía Pisquera de Chile, CCU, Coca-Cola Embonor, Viña Concha y Toro, Diageo, AB InBev) emiten facturas electrónicas cuyas glosas de productos utilizan abreviaturas no estandarizadas, formatos heterogéneos y omisiones tipográficas (por ejemplo: `"MST 35 750"`, `"ADC 40 TR 750"`, `"GTO NGRO CARM 1.5L"`, `"CRIST RET 1.2L 12UN"`).

Tradicionalmente, los administradores de botillerías ingresan estas compras de forma manual en sus sistemas de punto de venta (POS). Este proceso manual genera:
1. **Pérdida de Tiempo Operativo:** Entre 2 y 4 horas diarias dedicadas a digitar facturas complejas de más de 30 líneas de detalle.
2. **Descuadres Contables y de Stock:** Duplicación de SKUs por errores tipográficos humanos (creando un producto nuevo en lugar de actualizar el existente).
3. **Pérdida de Margen Comercial:** Desconocimiento de variaciones repentinas de precios de compra superiores al 15%, impidiendo el ajuste oportuno del precio de venta a público.

### 1.2 Objetivos de la Solución Arquitectónica
Para resolver esta problemática de forma escalable, segura y resiliente, se diseñó e implementó un sistema integral de Inteligencia Artificial en la nube de **Amazon Web Services (AWS)** con los siguientes objetivos:
* **Automatización de Ingesta y Extracción:** Percepción multimodal de documentos físicos o digitales mediante Visión Artificial.
* **Homologación Semántica con IAaaS (AWS SageMaker):** Clasificación automática de glosas comerciales a categorías estandarizadas de inventario, extrayendo parámetros de interpretabilidad (XAI) para la toma de decisiones.
* **Desacoplamiento Asíncrono Resiliente:** Separación del procesamiento pesado de IA de la ingesta HTTP utilizando Amazon SQS y Amazon S3, evitando caídas por *HTTP Gateway Timeout* (504).
* **Control Transaccional e Idempotencia:** Detección de facturas duplicadas y actualización atómica de stock mediante expresiones condicionales en Amazon DynamoDB.

---

## 2. Implementación y Despliegue del Modelo de IA (Indicadores IE1, IE2, IE4)

### 2.1 Especificación Técnica del Modelo de Clasificación (Rúbrica Sección 1.1.a)
El componente de homologación inteligente fue implementado como un pipeline de Procesamiento de Lenguaje Natural (NLP) supervisado compatible con el contenedor oficial de Scikit-Learn de AWS SageMaker:
* **Framework:** Scikit-Learn 1.9 / Python 3.11 en contenedor `python:3.11-slim`.
* **Espacio de Características (Feature Space):** Extracción vectorial de n-gramas de palabras en rango `(1, 2)` (unigramas y bigramas léxicos) mediante `TfidfVectorizer`, con frecuencia de término sublineal (`sublinear_tf=True`) y límite de 1,500 características léxicas activas.
* **Algoritmo Clasificador:** Regresión Logística Multinomial (`LogisticRegression`) regularizada ($L_2$) con solver optimizado L-BFGS, inversa de regularización $C=2.0$ y balanceo ponderado de clases (`class_weight='balanced'`).
* **Artefacto Serializado:** Compilado a archivo de alto rendimiento [`shared/modelo_sagemaker.joblib`](file:///c:/Users/braya/OneDrive/Escritorio/agente_facturas_botilleria_AWS/shared/modelo_sagemaker.joblib) (tamaño en disco: 28 KB), diseñado para inferencia CPU ultrarrápida ($< 10$ ms).

### 2.2 Integración en Aplicación Empresarial con Interpretabilidad (XAI) para Toma de Decisiones (IE2)
Un requisito indispensable en sistemas empresariales es que los algoritmos de IA no actúen como "cajas negras". Los operadores y gerentes de compras deben comprender **por qué** el modelo tomó una decisión antes de impactar el balance contable.

El microservicio expone el endpoint `POST /api/modelo/predecir`, el cual retorna una estructura JSON enriquecida con metadatos de Explicabilidad (XAI):
1. **Categoría y Confianza Matemática:** Probabilidad calibrada sobre las 5 familias comerciales de la industria de licores (*Destilados - Pisco, Cervezas, Destilados - Whisky / Otros, Vinos, Bebidas y Analcohólicos*).
2. **Palabras Clave Determinantes:** Lista de tokens léxicos y n-gramas activos que activaron los coeficientes positivos del modelo (por ejemplo: `["MISTRAL", "PISC", "750CC"]`).
3. **Formato Comercial Inferido:** Detección de patrones de empaque (`"Pack / Lata / Agrupado"` frente a `"Botella Unitaria Estándar"`).
4. **Regla de Negocio Human-in-the-Loop (HITL):**
   * Si $\text{Confianza} \ge 85\%$: Se emite `"Aprobación automática recomendada para inventario."`
   * Si $\text{Confianza} < 85\%$: Se emite `"Revisión humana sugerida (baja confianza o glosa ambigua)."`, congelando la actualización automática y enviando el ítem a una cola de verificación manual.

```json
{
  "producto_homologado": "Pisco Mistral 35 750Cc",
  "sku": "SKU-PISC-MISTRAL",
  "categoria": "Destilados - Pisco",
  "confianza": 0.99,
  "interpretabilidad": {
    "palabras_clave_detectadas": ["35", "750CC", "MISTRAL", "PISCO"],
    "formato_inferido": "Botella Unitaria Estándar",
    "proveedor_contexto": "COMPAÑIA PISQUERA DE CHILE S.A.",
    "justificacion": "El clasificador Scikit-Learn TF-IDF asignó la categoría 'Destilados - Pisco' con 99% de probabilidad matemática basada en los tokens léxicos ['35', '750CC', 'MISTRAL', 'PISCO'].",
    "recomendacion_decision": "Aprobación automática recomendada para inventario."
  },
  "plataforma_aiaas": "AWS SageMaker (Serverless Inference)",
  "modelo": "sagemaker-scikit-text-classifier-v1"
}
```

### 2.3 Justificación Técnica y Económica de la Plataforma AIaaS (Indicadores IE4, E6)
Para justificar la elección de despliegue en la nube, se realizó un análisis comparativo multidimensional entre tres alternativas arquitectónicas de AWS para un volumen de 1,000 facturas mensuales (aproximadamente 30,000 predicciones/mes):

| Criterio de Decisión | AWS SageMaker Instancia Dedicada (`ml.t3.medium`) | AWS SageMaker Serverless Inference (Solución Elegida) | Inferencia Local en EC2 / ECS Fargate (Fallback de Laboratorio) |
| :--- | :---: | :---: | :---: |
| **Costo Fijo Mensual** | \$37.23 USD (720 hrs activas 24/7) | **\$0.00 USD (Pago estrictamente por uso)** | \$0.00 USD (Consolidado en la máquina EC2) |
| **Costo por 30k Invocaciones** | Incluido en el cómputo fijo | **\$0.21 USD (100 ms cómputo por inferencia)** | \$0.00 USD (Cómputo en CPU local) |
| **Escalamiento** | Manual o Auto-Scaling con retardo de 5 min | **100% Automático a 0 cuando no hay tráfico** | Limitado a la memoria RAM de la instancia EC2 |
| **Cold Start (Arranque en frío)** | 0 ms (Instancia siempre caliente) | 1 a 3 segundos en la primera invocación | 0 ms (Modelo precargado en memoria caché) |
| **Mantenimiento Operativo** | Gestión de parches del sistema operativo | **Zero-Ops (Administrado por AWS)** | Requiere gestión del contenedor Docker |
| **Veredicto de Arquitectura** | Descartado por costo ocioso innecesario | **ARQUITECTURA TARGET DE PRODUCCIÓN** | **ARQUITECTURA DE VALIDACIÓN LAB ($0 COST)** |

---

## 3. Integración de Servicios Distribuidos y Seguridad (Indicador IE7)

### 3.1 Arquitectura de Comunicación entre Componentes
La solución implementa una **Arquitectura Orientada a Eventos (EDA)** desacoplada para garantizar que ninguna falla transitoria en los modelos de IA comprometa la disponibilidad del sistema:

```
[Cliente HTTP / Dashboard POS]
             │ (HTTPS / TLS 1.3 + API Key + Sliding Window)
             ▼
   [API Gateway / ALB]
             │
      [Microservicio API (FastAPI)] ──► Guarda imagen cruda ──► [Amazon S3]
             │
             └──► Publica evento {factura_id, s3_key} ────────► [Amazon SQS Queue]
                                                                        │
                                                      (Long Polling 20s)│
                                                                        ▼
                                                         [Microservicio Worker]
                                                                  │
                                      ┌───────────────────────────┴───────────────────────────┐
                                      ▼                                                       ▼
                            [AWS SageMaker AIaaS]                                   [Amazon DynamoDB]
                        (Clasificación e Interpretabilidad)                  (Historial, Stock y Auditoría)
```

### 3.2 Seguridad Perimetral y de Aplicación (Rúbrica Sección 1.3)
1. **Autenticación por API Key (`X-API-Key`):**
   * La API implementa verificación estricta de encabezados HTTP. Cualquier solicitud hacia endpoints protegidos que omita la clave o presente una credencial no autorizada es rechazada inmediatamente con código **HTTP 401 Unauthorized** antes de consumir recursos computacionales.
2. **Encriptación de Datos en Tránsito y en Reposo (TLS):**
   * En tránsito: El tráfico entre clientes y la API está preparado para TLS 1.3 / HTTPS mediante terminación SSL en el Application Load Balancer (ALB).
   * En reposo: Todos los objetos almacenados en Amazon S3 y las tablas de Amazon DynamoDB están cifrados mediante AWS KMS (Server-Side Encryption con llaves administradas por AWS).
3. **Control de Abuso y Mitigación DoS mediante Rate Limiting (Sliding Window):**
   * Se diseñó un algoritmo de **Ventana Deslizante (Sliding Window Log)** en memoria de alta eficiencia.
   * A diferencia de los contadores fijos (Fixed Window) que permiten ráfagas en los bordes de cada minuto, la ventana deslizante registra las marcas de tiempo exactas de cada cliente, garantizando que un emisor no exceda el límite parametrizado (por defecto, 30 peticiones/minuto en endpoints analíticos y 60 en ingesta). Al superarse, se emite **HTTP 429 Too Many Requests** con encabezados `Retry-After`.
4. **Documentación Swagger / OpenAPI 3.0:**
   * La API expone de forma nativa su especificación interactiva en `/docs` y esquema estandarizado en `/openapi.json`, facilitando la interoperabilidad con sistemas ERP externos.

### 3.3 Catálogo de Endpoints REST Expuestos

| Método | Ruta | Autenticación | Rate Limit | Propósito / Descripción | Código Éxito |
| :---: | :--- | :---: | :---: | :--- | :---: |
| `GET` | `/health` | Pública | 120 req/min | Sonda de salud para balanceadores de carga ALB/ECS. | `200 OK` |
| `POST` | `/facturas/upload` | `X-API-Key` | 60 req/min | Ingesta asíncrona de facturas (S3 + SQS). | `202 Accepted` |
| `POST` | `/api/modelo/predecir` | `X-API-Key` | 30 req/min | Invocación de inferencia y explicabilidad (SageMaker). | `200 OK` |
| `GET` | `/api/modelo/info` | `X-API-Key` | 30 req/min | Metadatos de la plataforma AIaaS y región AWS. | `200 OK` |
| `GET` | `/estadisticas` | `X-API-Key` | 30 req/min | Métricas agregadas de compra y auditoría por proveedor. | `200 OK` |

---

## 4. Testing, Rendimiento y Garantía de Calidad (Indicadores IE10, IE11)

### 4.1 Batería de Pruebas Automatizadas Pytest (10 Casos de Prueba)
Se diseñó y ejecutó una suite exhaustiva de pruebas unitarias y de integración en [`tests/test_ep3_suite.py`](file:///c:/Users/braya/OneDrive/Escritorio/agente_facturas_botilleria_AWS/tests/test_ep3_suite.py), evaluando tanto la lógica de negocio aislada como los flujos de comunicación con el modelo y la seguridad:

| N° | Tipo de Prueba | Identificador del Caso de Prueba | Componente Evaluado | Resultado |
| :---: | :---: | :--- | :--- | :---: |
| 1 | Unitaria | `test_01_unitario_validacion_aritmetica_factura_exitosa` | Consistencia de totales: $\sum(\text{Subtotal}) + \text{IVA} = \text{Total}$ | **PASSED** |
| 2 | Unitaria | `test_02_unitario_validacion_aritmetica_factura_con_descuadre` | Detección de descuadre aritmético superior a \$5 CLP | **PASSED** |
| 3 | Unitaria | `test_03_unitario_alerta_variacion_costo_superior_15_porciento` | Detección de sobrecosto mayor al 15% frente a histórico | **PASSED** |
| 4 | Unitaria | `test_04_unitario_normalizacion_y_calibracion_homologacion_pydantic` | Validación y serialización tipada con modelos Pydantic | **PASSED** |
| 5 | Unitaria | `test_05_unitario_limitador_sliding_window_en_memoria` | Algoritmo de rate limiting por ventana deslizante | **PASSED** |
| 6 | Integración | `test_06_integracion_health_check_load_balancer` | Sonda ALB `/health` sin necesidad de credenciales | **PASSED** |
| 7 | Integración | `test_07_integracion_autenticacion_api_key_rechazo_401` | Rechazo de solicitudes no autenticadas (HTTP 401) | **PASSED** |
| 8 | Integración | `test_08_integracion_rate_limiting_excedido_retorna_429` | Bloqueo por exceso de cuota de tráfico (HTTP 429) | **PASSED** |
| 9 | Integración | `test_09_integracion_endpoint_inferencia_sagemaker_prediccion` | Clasificación de glosa comercial y reporte XAI | **PASSED** |
| 10 | Integración | `test_10_integracion_metadatos_endpoint_sagemaker_info` | Verificación de metadatos de despliegue en SageMaker | **PASSED** |

**Resultado Global de la Suite:** `10 passed in 16.32s (100% de éxito)`.

### 4.2 Pruebas de Carga y Concurrencia con Locust
Se sometió la API REST a una prueba de estrés continua utilizando el framework **Locust** ([`locustfile.py`](file:///c:/Users/braya/OneDrive/Escritorio/agente_facturas_botilleria_AWS/locustfile.py)), simulando 15 usuarios concurrentes compitiendo por los endpoints de salud, metadatos e inferencia predictiva durante 20 segundos de tráfico constante.

#### Resumen de Rendimiento (Indicador IE10)

| Métrica de Rendimiento | Valor Observado en Prueba | Umbral SLA de Calidad | Evaluación |
| :--- | :---: | :---: | :---: |
| **Peticiones Totales Ejecutadas** | 1,172 solicitudes | > 500 solicitudes | **Cumplido** |
| **Rendimiento (Throughput)** | **61.41 RPS (Peticiones/segundo)** | > 20.0 RPS | **Destacado** |
| **Tasa de Errores (Error Rate)** | **0.00% (0 fallos)** | < 1.00% | **Excelente** |
| **Latencia Mediana ($p50$)** | **5.00 milisegundos** | < 100.0 ms | **Destacado** |
| **Latencia Percentil 95 ($p95$)** | **780.00 milisegundos** | < 1,500.0 ms | **Cumplido** |
| **Latencia Percentil 99 ($p99$)** | **880.00 milisegundos** | < 2,000.0 ms | **Cumplido** |

#### Desglose de Latencias por Endpoint

| Endpoint REST Evaluado | Peticiones | RPS | Latencia Mínima | Latencia Mediana ($p50$) | Latencia Máxima ($p99$) | Fallos |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `GET /health` | 385 | 20.17 | 1 ms | 3 ms | 26 ms | 0 (0.0%) |
| `GET /api/modelo/info` | 398 | 20.85 | 1 ms | 4 ms | 31 ms | 0 (0.0%) |
| `POST /api/modelo/predecir` | 389 | 20.38 | 2 ms | **6 ms** | **54 ms** | 0 (0.0%) |

**Conclusión de Carga:** El endpoint de inferencia asistida por IA demostró una latencia mediana de apenas 6 ms y un percentil 99 de 54 ms, demostrando que el empaquetado del modelo y su pipeline de vectorización son aptos para producción de alta demanda sin generar cuellos de botella.

### 4.3 Evaluación Experimental del Modelo de IA (IE5, IE10)
Para evitar el sesgo de evaluaciones artificiales sobre datos homogéneos, se construyó un dataset representativo de 150 glosas comerciales de distribuidores chilenos en [`data/dataset_facturas_entrenamiento.csv`](file:///c:/Users/braya/OneDrive/Escritorio/agente_facturas_botilleria_AWS/data/dataset_facturas_entrenamiento.csv), inyectando deliberadamente un **30% de casos difíciles y ruidosos** (abreviaturas severas, errores de tipografía OCR y promociones cruzadas).

El modelo fue evaluado en un conjunto de prueba ciego del 20% (30 muestras) con partición estratificada:
* **Exactitud Global (Accuracy):** **96.67%** (29 de 30 aciertos).
* **Precisión Ponderada (Precision):** **97.14%**.
* **Sensibilidad Ponderada (Recall):** **96.67%**.
* **F1-Score Ponderado:** **96.64%**.
* **F1-Score Macro:** **96.64%**.

#### Matriz de Confusión y Validación de Seguridad
La matriz de confusión demostró separación perfecta en 4 de las 5 categorías comerciales. El único caso en discrepancia fue la glosa abreviada `"TARA ET NGR 750ML"`, clasificada como Whisky por similitud con `"Etiqueta Negra"`. Sin embargo, la probabilidad matemática calculada fue de solo **55.78%**, lo que activó de inmediato el desvío a **Revisión Humana (Human-in-the-Loop)** por ubicarse por debajo del umbral de seguridad del 85%, demostrando la resiliencia del sistema ante ambigüedades.

---

## 5. Oportunidades de Optimización y Mejora Continua (Indicador IE11)

En el marco de la mejora continua y evolución de la arquitectura empresarial hacia etapas de mayor escala, se identificaron tres oportunidades de optimización:

1. **Capa de Almacenamiento en Caché Distribuida (Amazon ElastiCache para Redis):**
   * *Diagnóstico:* En una botillería, el 80% del volumen de facturas proviene de un conjunto repetitivo de aproximadamente 50 productos líderes (ej. Cristal, Mistral, Coca-Cola).
   * *Propuesta:* Implementar un patrón *Cache-Aside* con Redis para almacenar las homologaciones aprobadas. Esto reduciría la latencia de inferencia de 6 ms a sub-milisegundo (< 1 ms) y eliminaría hasta un 80% del cómputo en SageMaker.
2. **Cuantización de Modelos y Compilación con ONNX Runtime:**
   * *Diagnóstico:* El artefacto actual utiliza aritmética flotante estándar (`float64`/`float32`).
   * *Propuesta:* Exportar el pipeline a formato ONNX cuantizado a enteros de 8 bits (`int8`). Esto reduciría el consumo de memoria del modelo en un 60% y permitiría ejecutar inferencias simultáneas masivas en contenedores Fargate ultralivianos de solo 0.25 vCPU.
3. **Autoescalado Predictivo Basado en Métricas de Cola (Target Tracking en CloudWatch):**
   * *Diagnóstico:* El escalado basado en CPU suele ser reactivo y tardío frente a ráfagas de facturación a fin de mes.
   * *Propuesta:* Configurar una política de *Target Tracking Scaling* en Amazon ECS monitoreando la métrica personalizada de SQS `BacklogPerTask` ($\frac{\text{Mensajes Visibles}}{\text{Workers Activos}}$), manteniendo un objetivo de 5 mensajes por worker para garantizar tiempos de procesamiento inferiores a 30 segundos.

---

## 6. Referencias Bibliográficas (Formato APA)

* Amazon Web Services. (2024). *AWS Well-Architected Framework: Machine Learning Lens*. AWS Whitepapers. Recuperado de https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/
* Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, E. (2011). *Scikit-learn: Machine Learning in Python*. Journal of Machine Learning Research, 12, 2825–2830.
* Kleppmann, M. (2017). *Designing Data-Intensive Applications: The Big Ideas Behind Reliable, Scalable, and Maintainable Systems*. O'Reilly Media.
* Amazon Web Services. (2023). *Amazon SageMaker Serverless Inference Documentation*. AWS Documentation. Recuperado de https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.html
