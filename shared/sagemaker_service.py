"""Inferencia real en SageMaker con credenciales temporales entre cuentas.

No se cargan modelos locales ni se simulan predicciones si falla AWS.
Las credenciales originales del proyecto no se modifican.
"""
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)
SAGEMAKER_ENDPOINT_NAME = os.getenv("SAGEMAKER_ENDPOINT_NAME", "botilleria-classifier-demo-v1")
AWS_REGION = os.getenv("SAGEMAKER_REGION") or os.getenv("AWS_REGION", "us-east-1")


class SageMakerRuntime:
    def __init__(self):
        self._client = None
        self._expiration = None
        self._settings = None
        self._lock = threading.Lock()

    def get_client(self):
        region = os.getenv("SAGEMAKER_REGION") or os.getenv("AWS_REGION", "us-east-1")
        role_arn = os.getenv("SAGEMAKER_ROLE_ARN", "").strip()
        settings = (region, role_arn)
        with self._lock:
            ahora = datetime.now(timezone.utc)
            if self._client is not None and settings == self._settings and (
                self._expiration is None
                or ahora + timedelta(minutes=5) < self._expiration
            ):
                return self._client

            # Boto3 usa las credenciales del proyecto o el rol de EC2.
            # AWS_ENDPOINT_URL de LocalStack no se aplica a STS/SageMaker.
            kwargs = {"region_name": region}
            expiration = None
            if role_arn:
                credenciales = boto3.client("sts", region_name=region).assume_role(
                    RoleArn=role_arn,
                    RoleSessionName="ApiBotilleriaSageMaker",
                    DurationSeconds=3600,
                )["Credentials"]
                kwargs.update(
                    aws_access_key_id=credenciales["AccessKeyId"],
                    aws_secret_access_key=credenciales["SecretAccessKey"],
                    aws_session_token=credenciales["SessionToken"],
                )
                expiration = credenciales["Expiration"]
            client = boto3.client(
                "sagemaker-runtime", **kwargs,
                config=Config(connect_timeout=10, read_timeout=70,
                              retries={"mode": "standard", "total_max_attempts": 3}),
            )
            self._client = client
            self._expiration = expiration
            self._settings = settings
            return client


_runtime = SageMakerRuntime()


def get_sagemaker_runtime():
    """Obtiene el cliente cloud y renueva credenciales antes de su vencimiento."""
    return _runtime.get_client()


def predecir_con_sagemaker(
    glosa: str,
    proveedor: str = "Distribuidor General",
    precio_unitario: Optional[float] = None,
) -> Dict[str, Any]:
    endpoint = os.getenv("SAGEMAKER_ENDPOINT_NAME", SAGEMAKER_ENDPOINT_NAME).strip()
    if not endpoint:
        raise RuntimeError("SAGEMAKER_ENDPOINT_NAME no está configurado")
    inicio = time.perf_counter()
    respuesta = get_sagemaker_runtime().invoke_endpoint(
        EndpointName=endpoint,
        ContentType="application/json",
        Accept="application/json",
        Body=json.dumps({"glosa": glosa, "proveedor": proveedor,
                         "precio_unitario": precio_unitario}, ensure_ascii=False).encode("utf-8"),
    )
    cuerpo = respuesta["Body"]
    try:
        resultado = json.loads(cuerpo.read())
    finally:
        cuerpo.close()
    if not isinstance(resultado, dict):
        raise ValueError("SageMaker devolvió una respuesta inválida")
    resultado["modo_ejecucion"] = "AWS SageMaker Cloud Endpoint (Activo)"
    resultado["tiempo_inferencia_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
    logger.info("Predicción completada en SageMaker: %s", endpoint)
    return resultado
