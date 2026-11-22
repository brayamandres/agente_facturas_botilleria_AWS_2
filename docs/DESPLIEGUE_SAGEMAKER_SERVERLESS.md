# Despliegue del clasificador en SageMaker Serverless

**Fecha:** 22 de noviembre de 2026.  
**Región:** Norte de Virginia (`us-east-1`).

## 1. Qué se consiguió

Se desplegó en Amazon SageMaker un modelo que recibe la descripción de un producto y predice su categoría, por ejemplo, pisco, cerveza o vino.

El modelo ya estaba entrenado en el repositorio de GitHub. Lo reutilizamos y comprobamos una predicción mediante `sagemaker-runtime.invoke_endpoint`. Por lo tanto, la prueba final se ejecutó realmente en AWS.

**No se volvió a entrenar el modelo.** Posteriormente se conectó la ruta REST de la API al endpoint entre cuentas; el procesamiento automático del worker sigue pendiente. Ver [integración de la API](CONECTAR_API_SAGEMAKER.md).

## 2. Qué se hizo, paso a paso

1. **Se creó un cuaderno de SageMaker** llamado `botilleria-entrenamiento`, con instancia `ml.t3.medium`. Se utilizó como equipo de trabajo para preparar archivos, ejecutar comandos y probar el despliegue.
2. **Se creó un rol IAM**, para que SageMaker pudiera acceder a los recursos necesarios.
3. **Se subió el CSV a S3.** Tiene 150 registros. Se preparó una separación de 120 para entrenamiento y 30 para evaluación.
4. **Se intentó iniciar un entrenamiento administrado**, pero AWS lo rechazó porque la cuota de `ml.m5.large` para entrenamiento era cero. Ese intento no inició una máquina de entrenamiento.
5. **Se decidió reutilizar `shared/modelo_sagemaker.joblib` de GitHub.** El archivo contiene un clasificador TF-IDF y regresión logística. TF-IDF convierte el texto en números y la regresión logística selecciona una categoría.
6. **Se creó un entorno Python 3.11 con scikit-learn 1.9.0**, compatible con el archivo, y se verificó que podía cargarlo y predecir.
7. **Se empaquetó el modelo en `model.tar.gz`**, con el nombre interno `model.joblib`, y se subió a S3.
8. **Se preparó un servidor de predicción** con Flask y Gunicorn. La ruta `/ping` comprueba que funciona y `/invocations` recibe el texto y devuelve el resultado.
9. **Se construyó una imagen Docker**, incluyendo el servidor y las versiones de librerías comprobadas. El modelo se mantiene separado en S3; SageMaker lo carga en `/opt/ml/model` al iniciar el contenedor.
10. **Se probó la imagen y se subió a Amazon ECR**, el almacén de imágenes Docker de AWS.
11. **Se registró el modelo y se creó el endpoint Serverless.** Finalmente se envió una solicitud real y se recibió la predicción.

La solicitud de aumento de cuota de entrenamiento dejó de ser necesaria para esta ruta. Las cuotas del endpoint Serverless son independientes.

## 3. Para qué sirve cada recurso

| Recurso | Función |
|---|---|
| Cuaderno de SageMaker | Entorno de trabajo usado durante la preparación. |
| Amazon S3 | Guarda el CSV y el archivo del modelo entrenado. |
| Amazon ECR | Guarda la imagen Docker con el servidor y sus dependencias. |
| Rol IAM | Autoriza el acceso de SageMaker a los recursos. |
| Endpoint Serverless | Recibe solicitudes y ejecuta las predicciones. |
| CloudWatch | Permite consultar logs y métricas del endpoint. |

Flujo de una consulta:

```text
Cuaderno o aplicación
        |
        | invoke_endpoint con una glosa
        v
SageMaker Serverless
        |
        | ejecuta el modelo cargado desde S3
        v
Respuesta JSON con categoría y probabilidad
```

El cuaderno puede detenerse después del trabajo: el endpoint funciona de forma independiente. Las invocaciones se autentican con AWS; no se creó una API pública de libre acceso.

## 4. Configuración utilizada

| Parámetro | Valor |
|---|---|
| Modelo registrado | `botilleria-classifier-v1` |
| Configuración | `botilleria-serverless-v1` |
| Endpoint | `botilleria-classifier-demo-v1` |
| Memoria | 2048 MB |
| Solicitudes simultáneas máximas | 1 |
| Concurrencia provisionada | Sin configurar |
| Repositorio ECR | `sagemaker-botilleria-inferencia` |
| Modelo en S3 | `s3://sagemaker-botilleria-datos-2026/modelos/botilleria/v1/model.tar.gz` |

La concurrencia máxima de 1 es una configuración inicial para la demostración. Solicitudes simultáneas adicionales pueden recibir limitación de capacidad; todavía no se han realizado pruebas de carga para dimensionar el servicio.

## 5. Por qué Serverless y no un endpoint convencional

Un endpoint convencional de inferencia en tiempo real mantiene las instancias que se le asignan mientras está desplegado. Resulta útil cuando hay tráfico sostenido o se necesita una respuesta más predecible.

Serverless bajo demanda activa capacidad cuando llegan solicitudes y puede reducirla a cero cuando no hay tráfico. Esto encaja con un clasificador pequeño y una demostración académica, donde hay períodos largos sin consultas. No hace falta mantener una máquina de inferencia encendida durante todo el día. [Funcionamiento oficial de Serverless](https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.html).

| Aspecto | Serverless elegido | Endpoint convencional con instancias |
|---|---|---|
| Patrón adecuado | Consultas esporádicas o variables. | Tráfico continuo o más exigente. |
| Administración | Se elige memoria y concurrencia. | Se eligen instancias y políticas de escalado. |
| Tiempo sin consultas | Puede escalar a cero. | Las instancias asignadas siguen activas. |
| Primera respuesta tras inactividad | Puede tardar más por el arranque en frío. | El modelo puede estar ya cargado. |
| Capacidad de esta configuración | Una solicitud a la vez. | Depende del dimensionamiento. |

El arranque en frío es la principal desventaja aceptada para esta prueba. No se habilitó concurrencia provisionada porque mantener capacidad preparada agrega un costo. Serverless tampoco admite GPU, pero este clasificador utiliza CPU. [Características y limitaciones](https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.html).

## 6. Costos de referencia

**Importes en USD, antes de créditos, ofertas gratuitas e impuestos. Son estimaciones, no la factura de esta cuenta.** Referencias consultadas el 22 de noviembre de 2026; verificar la tarifa regional antes de presupuestar.

### Predicciones Serverless

El ejemplo oficial de AWS para 2 GB utiliza **USD 0,00004 por segundo de inferencia** y **USD 0,016 por GB procesado de entrada/salida**. [Precios de SageMaker, ejemplo 13](https://aws.amazon.com/sagemaker/ai/pricing/).

```text
Cómputo estimado = solicitudes × segundos facturables por solicitud × 0,00004
```

| Solicitudes | Duración supuesta por solicitud | Cómputo estimado |
|---:|---:|---:|
| 1.000 | 0,1 segundos | USD 0,004 |
| 30.000 | 0,1 segundos | USD 0,12 |
| 30.000 | 1 segundo | USD 1,20 |

No se ha medido la duración facturable real. Estas cifras excluyen datos procesados y servicios auxiliares.

### Comparación con un endpoint convencional

Como referencia, AWS publica `ml.c5.xlarge` a **USD 0,204/h** en su ejemplo de hosting. Una instancia durante 730 horas representa **USD 148,92**, más otros cargos. Es una comparación ilustrativa: la capacidad es diferente y no se evaluó la alternativa convencional más económica. [Precios, ejemplo 10](https://aws.amazon.com/sagemaker/ai/pricing/).

### Otros recursos que también cuentan

| Recurso | Qué se cobra |
|---|---|
| Cuaderno `ml.t3.medium` | Horas encendido y almacenamiento asociado. Su tarifa específica debe consultarse en Notebook Instances para `us-east-1`. |
| ECR privado | Referencia: USD 0,10 por GB al mes; una imagen almacenada de 0,5 GB supondría aproximadamente USD 0,05/mes. |
| S3 | Almacenamiento del CSV y modelo, solicitudes y transferencias aplicables. |
| CloudWatch | Logs, retención y métricas u operaciones facturables utilizadas. |
| Nuevo entrenamiento | No se ejecutó: se reutilizó el archivo existente. El cuaderno sí estuvo funcionando. |

Fuentes: [ECR](https://aws.amazon.com/ecr/pricing/), [Notebook Instances y SageMaker](https://aws.amazon.com/sagemaker/ai/pricing/), [S3](https://aws.amazon.com/s3/pricing/) y [CloudWatch](https://aws.amazon.com/cloudwatch/pricing/).

**Serverless no significa que toda la solución sea gratuita.** Los créditos y beneficios aplicables pueden cubrir consumo, pero el importe efectivo debe comprobarse en Billing and Cost Management. No se ha consultado la facturación de la cuenta.

Para calcular el total real hacen falta las horas de uso del cuaderno, almacenamiento, tamaño de la imagen, llamadas, duración facturable y logs. En una demostración pequeña, dejar el cuaderno encendido puede pesar más que las predicciones.

## 7. Resultado comprobado y alcance

La prueba realizada por el usuario con SageMaker Runtime devolvió:

```json
{
  "categoria": "Destilados - Pisco",
  "confianza": 0.7994656614446165,
  "producto_homologado": "PISCO MISTRAL 35 750CC",
  "sku": null
}
```

La probabilidad máxima fue aproximadamente **79,95 %**. Es la salida de `predict_proba` para esta solicitud, no una medición de accuracy ni una garantía de acierto. En esta etapa no se realizó una nueva evaluación completa del modelo.

Los tokens devueltos muestran características presentes en el texto; no constituyen por sí solos una explicación de cuánto contribuyó cada palabra. El clasificador predice categorías, no identifica un SKU. El campo `producto_homologado` conserva el texto recibido y no demuestra una homologación contra el catálogo.

La evidencia inicial es la respuesta de la invocación mostrada en el cuaderno. Posteriormente se verificó la API REST con HTTP 200 contra el endpoint real entre cuentas. Falta conectar el worker, recopilar métricas de carga y completar la evidencia de CloudWatch para documentar el flujo completo.

## 8. Qué hacer al terminar de trabajar

1. Guardar el cuaderno y detener `botilleria-entrenamiento`; sus archivos se conservan, aunque el almacenamiento continúa.
2. Mantener el endpoint si se necesita demostrar o integrar el modelo. Bajo demanda puede escalar a cero; no tiene concurrencia provisionada.
3. Revisar el consumo y saldo de créditos en la consola de facturación.
4. Cuando ya no se necesite el despliegue, eliminar el endpoint y después sus recursos asociados que no se quieran conservar. Borrar solo el endpoint no elimina S3, las imágenes de ECR, el cuaderno ni los logs.

