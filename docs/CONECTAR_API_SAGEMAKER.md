# API conectada a SageMaker entre cuentas

La API del proyecto utiliza sus credenciales originales para los datos. Solo el cliente de SageMaker obtiene credenciales temporales mediante STS `AssumeRole`.

## Configuración

En el `.env` de la raíz:

```dotenv
SAGEMAKER_REGION=us-east-1
SAGEMAKER_ENDPOINT_NAME=botilleria-classifier-demo-v1
SAGEMAKER_ROLE_ARN=arn:aws:iam::844222058442:role/BotilleriaSageMakerInvokeRole
API_KEY=una-clave-propia
```

`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y, cuando corresponda, `AWS_SESSION_TOKEN` siguen siendo de la cuenta del proyecto. No guardar las credenciales temporales de la prueba manual en el archivo: el servicio las obtiene y las renueva cinco minutos antes de vencer, al llegar una solicitud.

La configuración actual autoriza a `arn:aws:iam::663345616583:user/brayamprincipal` a asumir el rol de la cuenta `844222058442`. El rol permite `sagemaker:InvokeEndpoint` sobre `botilleria-classifier-demo-v1` en `us-east-1`. Al mover la API a EC2, autorizar el rol de esa EC2 en la confianza de destino y darle `sts:AssumeRole`; no depende de que el usuario IAM siga siendo la identidad del servidor.

## Aplicar y probar

Si todavía estás en el intérprete Python de la prueba manual, escribe `exit()`.

Desde la raíz del proyecto:

```powershell
docker compose up -d --build --no-deps --force-recreate api
```

Abre <http://localhost:8000/docs>. En **Authorize**, introduce el valor de `API_KEY` de tu `.env`. Después ejecuta `POST /api/modelo/predecir` con:

```json
{
  "glosa": "PISCO MISTRAL 35 750CC",
  "proveedor": "CCU",
  "precio_unitario": 5490
}
```

Se espera la categoría `Destilados - Pisco`, una probabilidad aproximada de `0.7994656614446165` para la versión desplegada y `modo_ejecucion` igual a `AWS SageMaker Cloud Endpoint (Activo)`. El tiempo incluye la conexión y, cuando se renueva, la obtención de credenciales, no solo el cómputo del modelo.

La ruta se ejecuta en el pool de hilos de FastAPI para que la llamada síncrona de boto3 no bloquee el bucle de eventos. Se conserva la autenticación y el rate limiting existentes de AWS_2; configura una API_KEY propia.

## Errores

| Código HTTP | Significado |
|---|---|
| 401 | Falta la cabecera `X-API-Key` o su valor es incorrecto. |
| 422 | Entrada inválida, por ejemplo una glosa vacía. |
| 503 | Falta configuración, o falló STS/SageMaker. Consultar logs. |

```powershell
docker compose logs --tail=80 api
```

La ruta no usa simulación, no aumenta la probabilidad del modelo y no actualiza stock. Agrega el consumo REST del clasificador; la integración dentro del grafo de facturas es un paso separado. Se utilizan las rutas y controles de acceso existentes de AWS_2; no se agrega una ruta duplicada.

## Verificación realizada

Se ejecutaron nueve pruebas aisladas, sin red ni llamadas a AWS, que cubren renovación de credenciales, separación de clientes, respuestas, autenticación y fallos. También se verificaron el inicio de la API completa, `/health` y la publicación de la ruta en OpenAPI.

En el checkout original, antes de portar la integración, se probó la ruta HTTP real `POST /api/modelo/predecir` con una invocación al endpoint entre cuentas. Respondió HTTP 200, categoría `Destilados - Pisco`, probabilidad `0.7994656614446165` y modo cloud activo. La primera prueba identificó un nombre de endpoint antiguo en `.env`; se corrigió a `botilleria-classifier-demo-v1` y la siguiente prueba fue satisfactoria. No se alteraron las credenciales de los demás servicios.

## Portabilidad a AWS_2

La integración vive en `shared/sagemaker_service.py`, conservando las funciones públicas usadas por la API y el módulo del worker. La ruta existente `/api/modelo/predecir` utiliza el conector real y devuelve 503 si falla AWS. Ya no hay respaldo local silencioso. La prueba real en esta carpeta se registra al verificar el despliegue.

## Verificacion en la carpeta correcta

El 22 de noviembre de 2026 se ejecutaron nueve pruebas aisladas satisfactoriamente en arqui_facturasV2/agente_facturas_botilleria_AWS_2. Ademas se invoco la ruta FastAPI real mediante TestClient, dentro de un contenedor temporal con el codigo de esa carpeta y acceso a AWS: devolvio HTTP 200, categoria Destilados - Pisco y probabilidad 0.7994656614446165. El contenedor permanente del proyecto anterior no se reemplazo durante esta comprobacion. No se crearon commits ni se publicaron estos cambios en GitHub.

## Autenticacion de las rutas del modelo

GET /api/modelo/info y POST /api/modelo/predecir exigen una cabecera X-API-Key valida,
tambien cuando se llaman desde Swagger o desde el mismo sitio. Referer y Sec-Fetch-Site
no autentican al usuario. El parametro de consulta api_key no sustituye la cabecera.
Sin cabecera o con clave incorrecta se devuelve HTTP 401 antes de invocar AWS.
Si API_KEY esta vacia, se devuelve HTTP 503. Las otras rutas conservan sus validadores existentes.
En Swagger, usar Authorize para enviar la clave; si ya estaba autorizado, usar Logout para
probar el caso sin clave. Tambien se puede verificar sin clave con curl desde una terminal.
