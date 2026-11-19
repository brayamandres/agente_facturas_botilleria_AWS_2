"""
Módulo de Inferencia con AWS SageMaker para el Worker.
Reexporta el servicio compartido de SageMaker para consumo del agente LangGraph.
"""
from shared.sagemaker_service import (
    predecir_con_sagemaker,
    get_sagemaker_runtime,
    SAGEMAKER_ENDPOINT_NAME
)

__all__ = ["predecir_con_sagemaker", "get_sagemaker_runtime", "SAGEMAKER_ENDPOINT_NAME"]
