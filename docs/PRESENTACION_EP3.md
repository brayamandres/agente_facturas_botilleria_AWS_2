# Estructura Oficial de Presentación y Defensa Oral (Evaluación Parcial N°3)

**Asignatura:** ITY1102 - Arquitectura de Sistemas de Inteligencia Artificial  
**Tiempo Máximo Asignado:** 15 minutos de presentación + ronda de preguntas  
**Límite de Láminas de Apoyo:** Máximo 6 láminas  
**Ponderación:** 40% de la nota final  
**Archivo de Presentación:** `EP3_Presentacion_Equipo[N].pdf`  

---

## Estructura General de Tiempo (Total: 13 Minutos de Exposición)

| Lámina | Título / Tema Principal | Indicadores Clave | Tiempo Estimado |
| :---: | :--- | :---: | :---: |
| **Lámina 1** | Contexto Empresarial y Caso de Negocio Retail | **IE3, IE5** | 02:00 min |
| **Lámina 2** | Arquitectura Distribuida en AWS y Flujo Orientado a Eventos | **IE7, IE8** | 02:30 min |
| **Lámina 3** | Plataforma AIaaS: Despliegue en AWS SageMaker y Justificación Económica | **IE1, IE4, E6** | 02:00 min |
| **Lámina 4** | Inferencia con Interpretabilidad (XAI) y Patrón Human-in-the-Loop | **IE2** | 02:30 min |
| **Lámina 5** | Garantía de Calidad: Pytest, Pruebas de Carga Locust y Métricas ML | **IE10, IE11** | 02:30 min |
| **Lámina 6** | Demostración en Vivo, Optimización Continua y Conclusiones | **IE9, IE11, IE12, IE13** | 01:30 min |

---

## Detalle Diapositiva por Diapositiva

### Lámina 1: Portada y Contexto Empresarial Retail
* **Título:** Sistema Distribuido de Inteligencia Artificial para Homologación Automática de Facturas e Inventario en AWS.
* **Subtítulo:** Solución Asíncrona Resiliente con Visión Multimodal, NLP en SageMaker e Interpretabilidad (XAI).
* **Contenido Visual:**
  * Diagrama comparativo: Proceso Tradicional Manual (2-4 hrs/día, errores tipográficos, pérdida de margen) vs. Sistema Automatizado con IA (Ingesta en $<1$ seg, conciliación automática, alertas de sobrecosto $>15\%$).
  * Métricas de Impacto: Reducción del 95% del tiempo de digitación, 0 duplicidad de SKUs, trazabilidad contable total.
* **Guión Oral del Expositor (02:00 min):**
  > *"Muy buenos días profesor y miembros de la comisión. En el comercio minorista y cadenas de botillerías en Chile, la recepción de mercadería presenta un grave cuello de botella: los distribuidores líderes como CCU, Capel o Embonor emiten facturas electrónicas con glosas informales y abreviaturas como 'MST 35 750' o 'CRIST RET 1.2L'.*
  >
  > *La digitación manual de estas facturas consume entre 2 y 4 horas diarias a los administradores, generando errores contables, duplicación involuntaria de productos en bodega y, lo más grave, la imposibilidad de reaccionar oportunamente ante variaciones imprevistas en los costos de compra.*
  >
  > *Para resolver esto de raíz, diseñamos e implementamos una solución empresarial en la nube de Amazon Web Services que automatiza la ingesta de documentos, la extracción multimodal con visión artificial, la homologación semántica mediante Machine Learning y la actualización atómica de inventario, integrando salvaguardas de interpretabilidad y seguridad perimetral."*

---

### Lámina 2: Arquitectura Final Desplegada en AWS y Flujo Orientado a Eventos
* **Título:** Arquitectura Distribuida Orientada a Eventos (Event-Driven Architecture)
* **Contenido Visual:**
  * Diagrama de arquitectura de AWS:
    * **Cliente Web / Dashboard** $\rightarrow$ **Application Load Balancer (ALB)** con terminación TLS.
    * **Microservicio API (FastAPI):** I/O Bound, contenedor `python:3.11-slim`, responde **HTTP 202 Accepted** en 120 ms.
    * **Amazon S3:** Bucket `botilleria-facturas-raw` para almacenamiento inmutable de imágenes de facturas.
    * **Amazon SQS:** Cola `botilleria-facturas-queue` desacoplando la ingesta del procesamiento pesado.
    * **Microservicio Worker (LangGraph AI):** Consumidor asíncrono con Long Polling (20s) y arquitectura Stateless.
    * **Amazon DynamoDB:** Tablas con Búsqueda Vectorial Nativa (`VectorIndexes`) y actualización atómica `ADD`.
* **Guión Oral del Expositor (02:30 min):**
  > *"Un principio fundamental de nuestra propuesta arquitectónica (IE8) fue superar las deficiencias de los sistemas monolíticos previos. En un monolito, la recepción HTTP competía con el cómputo pesado de inferencia de IA, provocando saturación de memoria y caídas por timeout.*
  >
  > *Nuestra solución adopta una Arquitectura Orientada a Eventos basada en microservicios desacoplados:*
  > *Primero, un microservicio de API ultraliviano (~120 MB RAM) recibe la factura, almacena la imagen en Amazon S3 y deposita un evento en Amazon SQS, retornando de inmediato un código HTTP 202 Accepted al usuario en menos de 150 milisegundos.*
  > *Segundo, la carga pesada de inferencia y orquestación con LangGraph es consumida asíncronamente por el Worker mediante Long Polling. Esto garantiza que ante picos repentinos de 100 facturas simultáneas, la API no se degrada y la cola SQS absorbe la demanda sin perder ningún mensaje, logrando tolerancia a fallos y desacoplamiento temporal garantizado."*

---

### Lámina 3: Plataforma AIaaS: AWS SageMaker y Justificación Económica
* **Título:** Integración de Inteligencia Artificial como Servicio (AIaaS) en AWS SageMaker
* **Contenido Visual:**
  * Tabla comparativa de decisiones de despliegue (Dedicated vs. Serverless vs. Local Fallback):
    * Instancia Dedicada `ml.t3.medium`: \$37.23 USD/mes fijos (inviable para PYMEs).
    * **AWS SageMaker Serverless Inference:** \$0.00 costo base + \$0.21 USD por 30,000 predicciones/mes.
    * Inferencia Local / EC2: Modo fallback para laboratorio académico a \$0 costo.
  * Pipeline de Clasificación NLP: Vectorización TF-IDF (1,500 características léxicas) + Regresión Logística Multinomial regularizada ($C=2.0$).
* **Guión Oral del Expositor (02:00 min):**
  > *"Para cumplir con los indicadores IE1, IE4 y E6, analizamos técnica y económicamente la mejor plataforma de despliegue cloud para el modelo de clasificación de productos.*
  >
  > *Descartamos el uso de instancias dedicadas en SageMaker debido a que mantener una máquina ml.t3.medium encendida 24/7 representa un costo fijo de \$37 dólares mensuales, con recursos ociosos durante la noche y fines de semana.*
  >
  > *En su lugar, optamos por **AWS SageMaker Serverless Inference**. Esta modalidad escala automáticamente a cero cuando no hay facturas que procesar, cobrando estrictamente por los milisegundos de cómputo utilizados. Para el volumen operacional de una botillería mediana (30,000 ítems clasificados al mes), el costo mensual es de apenas \$0.21 dólares, logrando una reducción del 99.4% en costos operativos sin sacrificar disponibilidad ni rendimiento."*

---

### Lámina 4: Inferencia con Interpretabilidad (XAI) y Patrón Human-in-the-Loop
* **Título:** Interpretabilidad Algorítmica (XAI) y Salvaguarda Operativa Human-in-the-Loop (HITL)
* **Contenido Visual:**
  * Flujograma de decisión condicional:
    * Input Glosa $\rightarrow$ Inferencia SageMaker $\rightarrow$ Cálculo de Probabilidad Matemática ($P$).
    * ¿$P \ge 85\%$? $\rightarrow$ **SÍ:** Aprobación automática e ingreso directo a stock.
    * ¿$P < 85\%$? $\rightarrow$ **NO:** Desvío a Revisión Humana (Human-in-the-Loop).
  * Ejemplo de Respuesta JSON del endpoint `/api/modelo/predecir` mostrando:
    * `confianza`: 0.99
    * `palabras_clave_detectadas`: `["35", "750CC", "MISTRAL", "PISCO"]`
    * `recomendacion_decision`: `"Aprobación automática recomendada para inventario."`
* **Guión Oral del Expositor (02:30 min):**
  > *"Un modelo de Inteligencia Artificial en un entorno empresarial no puede operar como una caja negra (IE2). En contabilidad e inventario, una predicción errónea altera los balances financieros y los impuestos específicos a los licores.*
  >
  > *Por ello, nuestro endpoint /api/modelo/predecir implementa interpretabilidad nativa (XAI): extrae los coeficientes de los n-gramas léxicos y entrega la probabilidad matemática exacta de la decisión.*
  >
  > *Establecimos una regla de negocio rigurosa: si la confianza matemática es igual o superior al 85%, el sistema aprueba la homologación automáticamente. Pero si la confianza es inferior al 85% —como ocurrió en nuestras pruebas de estrés con la glosa abreviada 'TARA ET NGR 750' que obtuvo solo 55.78% de certeza—, el sistema activa automáticamente el patrón Human-in-the-Loop, alertando al administrador para su validación manual y evitando la corrupción del catálogo."*

---

### Lámina 5: Estrategia de Testing Integral, Rendimiento y Métricas de Calidad
* **Título:** Validación Rigurosa: Pytest Automatizado, Pruebas de Carga Locust y Métricas ML
* **Contenido Visual:**
  * **Suite Pytest (10/10 Passed):** 5 pruebas unitarias (aritmética, alertas de sobrecosto, sliding window) + 5 de integración (auth 401, rate limit 429, inferencia SageMaker).
  * **Pruebas de Carga Locust (15 usuarios concurrentes por 20s):**
    * Throughput: **61.41 RPS** (1,172 solicitudes exitosas).
    * Tasa de errores: **0.00%**.
    * Latencia Inferencia SageMaker: Mediana **$p50 = 6\text{ ms}$**, Percentil **$p99 = 54\text{ ms}$**.
  * **Métricas del Modelo (Dataset 150 muestras, 30% casos ruidosos):**
    * Accuracy: **96.67%** | Precision: **97.14%** | Recall: **96.67%** | F1-Score: **96.64%**.
* **Guión Oral del Expositor (02:30 min):**
  > *"Para verificar la eficacia y robustez del sistema bajo los estándares del indicador IE10, implementamos una estrategia de calidad en tres niveles:*
  > *1. Pruebas Automatizadas:* Construimos una suite en Pytest con 10 casos de prueba que validan la consistencia matemática de facturas, la detección de alzas de costos superiores al 15%, la seguridad de la API y el rechazo con código 401 y 429 ante solicitudes indebidas. La suite se ejecuta en 16 segundos con 100% de aprobación.
  > *2. Pruebas de Carga:* Con Locust simulamos 15 usuarios concurrentes generando 1,172 solicitudes. La API sostuvo un throughput de 61.4 peticiones por segundo con 0% de errores, y el endpoint de inferencia IA respondió con una latencia mediana de apenas 6 milisegundos.
  > *3. Rendimiento del Modelo:* Entrenamos con 150 glosas reales inyectando un 30% de casos ruidosos y abreviados. En evaluación ciega obtuvimos un 96.67% de exactitud y un F1-Score de 96.64%, ubicándonos en el nivel Destacado de la rúbrica."*

---

### Lámina 6: Demostración en Vivo, Optimización Continua y Conclusiones
* **Título:** Demostración en Vivo, Mejoras Futuras y Cierre del Proyecto
* **Contenido Visual:**
  * Terminal y Swagger UI ejecutando:
    1. `GET /health` $\rightarrow$ `HTTP 200 OK` (Sonda ALB activa).
    2. `POST /api/modelo/predecir` $\rightarrow$ Inferencia en tiempo real con payload de factura chilena.
    3. `POST /facturas/upload` $\rightarrow$ Ingesta asíncrona con `HTTP 202 Accepted`.
  * Roadmap de Optimización (IE11):
    * Caché distribuida en Amazon ElastiCache (Redis) para reducir inferencias repetitivas a $< 1\text{ ms}$.
    * Cuantización a `int8` con ONNX Runtime para reducir el uso de memoria en un 60%.
    * Autoescalado de tareas ECS monitoreando la métrica de cola `BacklogPerTask` de SQS.
* **Guión Oral del Expositor (01:30 min):**
  > *"En la demostración en vivo (IE9) observamos cómo nuestra API protegida procesa solicitudes en tiempo real: el health check valida la disponibilidad para el balanceador, el endpoint de inferencia clasifica instantáneamente un ítem de Pisco Mistral con 99% de confianza y explicación léxica, y la ingesta asíncrona confirma la recepción de facturas en menos de 150 milisegundos.*
  >
  > *Como oportunidades de optimización en el marco de la mejora continua (IE11), hemos proyectado una capa de almacenamiento en caché con Amazon ElastiCache Redis para el 80% de los productos de alta rotación, y la cuantización del modelo a enteros de 8 bits con ONNX Runtime.*
  >
  > *Concluimos que la arquitectura implementada en AWS no solo cumple al 100% con todos los requerimientos de la rúbrica institucional, sino que entrega una solución industrial, económica y altamente confiable para el comercio chileno. Muchas gracias, quedamos atentos a sus preguntas."*

---

## Banco de Preguntas Difíciles Anticipadas de la Comisión Docente

### Pregunta 1: *"¿Por qué utilizaron una cola SQS y almacenamiento S3 intermedio en lugar de procesar la factura directamente en la llamada HTTP?"*
* **Respuesta Técnica Sugerida (IE8):**
  > *"Implementamos el desacoplamiento con S3 y SQS para garantizar la resiliencia y escalabilidad del sistema ante variaciones de carga. La inferencia multimodal y el razonamiento de homologación pueden tardar entre 10 y 20 segundos. Si lo ejecutáramos de forma síncrona, bloquearíamos los hilos del servidor web, expondríamos la API a errores 504 Gateway Timeout y agotaríamos los recursos de memoria. Con SQS y S3, la API responde HTTP 202 en milisegundos, los mensajes quedan persistidos de forma segura en la cola, y los workers procesan la carga a su propio ritmo con reintentos automáticos si ocurre cualquier falla transitoria."*

### Pregunta 2: *"¿Cómo aseguran que el modelo de Machine Learning no cometa errores críticos que alteren el inventario contable?"*
* **Respuesta Técnica Sugerida (IE2):**
  > *"Lo aseguramos mediante el patrón Human-in-the-Loop y calibración de confianza probabilística. El modelo no solo entrega una categoría, sino que calcula su certeza matemática exacta mediante predict_proba y extrae los tokens determinantes. Configuramos un umbral estricto del 85%: cualquier glosa ambigua o con baja probabilidad —como abreviaciones confusas o productos no catalogados— es marcada automáticamente para revisión humana antes de impactar el inventario en DynamoDB."*

### Pregunta 3: *"¿Qué diferencia existe entre un Rate Limiting de Ventana Fija y la Ventana Deslizante (Sliding Window) que implementaron?"*
* **Respuesta Técnica Sugerida (IE7):**
  > *"El limitador de Ventana Fija (Fixed Window) reinicia su contador al inicio de cada minuto (ej. de 12:00 a 12:01). Esto genera una vulnerabilidad en los bordes: un cliente podría enviar 30 solicitudes a las 12:00:59 y 30 más a las 12:01:01, acumulando 60 peticiones en 2 segundos sin ser bloqueado. Nuestra implementación de Ventana Deslizante (Sliding Window Log) almacena los timestamps exactos de cada cliente en un rango dinámico de 60 segundos hacia atrás, garantizando que en ningún intervalo continuo de 60 segundos se supere la cuota establecida."*
