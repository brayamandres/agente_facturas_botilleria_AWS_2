"""Acceso entre cuentas y rutas reales, con AWS reemplazado en las pruebas."""
import io
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from shared import sagemaker_service as servicio


def resultado_modelo():
    return dict(producto_homologado="PISCO MISTRAL 35 750CC", sku=None,
                categoria="Destilados - Pisco", confianza=0.7994656614446165,
                interpretabilidad={"palabras_clave_detectadas": ["pisco", "mistral"]},
                plataforma_aiaas="AWS SageMaker (Serverless Inference)",
                modelo="botilleria-tfidf-logreg-v1")


class ConexionTests(unittest.TestCase):
    def setUp(self):
        self.entorno = patch.dict(os.environ, {
            "SAGEMAKER_REGION": "us-east-1", "SAGEMAKER_ENDPOINT_NAME": "endpoint-prueba",
            "SAGEMAKER_ROLE_ARN": "arn:aws:iam::222222222222:role/Invocar",
            "AWS_ACCESS_KEY_ID": "origen", "AWS_SECRET_ACCESS_KEY": "origen-secreto",
            "AWS_ENDPOINT_URL": "http://localstack",
        })
        self.entorno.start()
        self.addCleanup(self.entorno.stop)

    def test_renovacion_y_separacion_de_credenciales(self):
        sts, runtime = Mock(), Mock()
        sts.assume_role.return_value = {"Credentials": {
            "AccessKeyId": "destino", "SecretAccessKey": "destino-secreto", "SessionToken": "token",
            "Expiration": datetime.now(timezone.utc) + timedelta(hours=1),
        }}
        proveedor = servicio.SageMakerRuntime()
        with patch.object(servicio.boto3, "client", side_effect=[sts, runtime, sts, runtime]) as crear:
            self.assertIs(proveedor.get_client(), runtime)
            self.assertIs(proveedor.get_client(), runtime)
            self.assertEqual(sts.assume_role.call_count, 1)
            self.assertEqual(crear.call_args.kwargs["aws_access_key_id"], "destino")
            self.assertNotIn("endpoint_url", crear.call_args.kwargs)
            self.assertEqual(os.environ["AWS_ACCESS_KEY_ID"], "origen")
            proveedor._expiration = datetime.now(timezone.utc) + timedelta(minutes=1)
            proveedor.get_client()
            self.assertEqual(sts.assume_role.call_count, 2)

    def test_misma_cuenta_usa_cadena_de_credenciales_normal(self):
        with patch.dict(os.environ, {"SAGEMAKER_ROLE_ARN": ""}), patch.object(servicio.boto3, "client") as crear:
            servicio.SageMakerRuntime().get_client()
            self.assertEqual(crear.call_args.args, ("sagemaker-runtime",))
            self.assertNotIn("aws_access_key_id", crear.call_args.kwargs)

    def test_probabilidad_real_y_cierre_de_respuesta(self):
        runtime = Mock()
        body = io.BytesIO(json.dumps(resultado_modelo()).encode())
        runtime.invoke_endpoint.return_value = {"Body": body}
        with patch.object(servicio, "get_sagemaker_runtime", return_value=runtime):
            resultado = servicio.predecir_con_sagemaker("PISCO", "CCU", 5490)
        self.assertTrue(body.closed)
        self.assertEqual(resultado["confianza"], 0.7994656614446165)
        self.assertEqual(resultado["modo_ejecucion"], "AWS SageMaker Cloud Endpoint (Activo)")
        self.assertEqual(runtime.invoke_endpoint.call_args.kwargs["EndpointName"], "endpoint-prueba")

    def test_error_aws_no_activa_simulacion(self):
        runtime = Mock()
        runtime.invoke_endpoint.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "denegado"}}, "InvokeEndpoint")
        with patch.object(servicio, "get_sagemaker_runtime", return_value=runtime):
            with self.assertRaises(ClientError):
                servicio.predecir_con_sagemaker("PISCO")

    def test_endpoint_vacio_no_invoca_aws(self):
        with patch.dict(os.environ, {"SAGEMAKER_ENDPOINT_NAME": ""}), patch.object(servicio, "get_sagemaker_runtime") as obtener:
            with self.assertRaises(RuntimeError):
                servicio.predecir_con_sagemaker("PISCO")
            obtener.assert_not_called()


class RutasTests(unittest.TestCase):
    def setUp(self):
        from api.main import app
        self.cliente = TestClient(app)
        self.clave = patch("api.security.API_KEY", "prueba")
        self.clave.start()
        self.addCleanup(self.clave.stop)
        self.headers = {"X-API-Key": "prueba"}

    def test_ruta_sin_clave_no_invoca_aws(self):
        with patch.object(servicio, "predecir_con_sagemaker") as invocar:
            self.assertEqual(self.cliente.post("/api/modelo/predecir", json={"glosa": "PISCO"}).status_code, 401)
            invocar.assert_not_called()

    def test_ruta_aws_falla_sin_ocultar_error(self):
        with patch.object(servicio, "predecir_con_sagemaker", side_effect=RuntimeError("detalle-interno")):
            respuesta = self.cliente.post("/api/modelo/predecir", headers=self.headers, json={"glosa": "PISCO"})
        self.assertEqual(respuesta.status_code, 503)
        self.assertNotIn("detalle-interno", respuesta.text)

    def test_ruta_conserva_contrato_y_probabilidad(self):
        datos = {**resultado_modelo(), "tiempo_inferencia_ms": 15,
                 "modo_ejecucion": "AWS SageMaker Cloud Endpoint (Activo)"}
        with patch.object(servicio, "predecir_con_sagemaker", return_value=datos):
            respuesta = self.cliente.post("/api/modelo/predecir", headers=self.headers, json={"glosa": "PISCO"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["confianza"], datos["confianza"])

    def test_entrada_vacia_no_invoca_aws(self):
        with patch.object(servicio, "predecir_con_sagemaker") as invocar:
            self.assertEqual(self.cliente.post("/api/modelo/predecir", headers=self.headers, json={"glosa": "   "}).status_code, 422)
            invocar.assert_not_called()


    def test_origen_de_navegador_no_omite_clave(self):
        with patch.object(servicio, "predecir_con_sagemaker") as invocar:
            for headers in [
                {"sec-fetch-site": "same-origin"},
                {"sec-fetch-site": "same-site"},
                {"referer": "http://testserver/docs"},
            ]:
                with self.subTest(headers=headers):
                    respuesta = self.cliente.post("/api/modelo/predecir", headers=headers, json={"glosa": "PISCO"})
                    self.assertEqual(respuesta.status_code, 401)
            invocar.assert_not_called()

    def test_query_no_sustituye_cabecera(self):
        with patch.object(servicio, "predecir_con_sagemaker") as invocar:
            respuesta = self.cliente.post("/api/modelo/predecir?api_key=prueba", json={"glosa": "PISCO"})
            self.assertEqual(respuesta.status_code, 401)
            invocar.assert_not_called()

    def test_clave_incorrecta_no_invoca_aws(self):
        with patch.object(servicio, "predecir_con_sagemaker") as invocar:
            respuesta = self.cliente.post("/api/modelo/predecir", headers={"X-API-Key": "incorrecta"}, json={"glosa": "PISCO"})
            self.assertEqual(respuesta.status_code, 401)
            invocar.assert_not_called()

    def test_info_tambien_exige_cabecera(self):
        respuesta = self.cliente.get("/api/modelo/info", headers={"referer": "http://testserver/docs"})
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(self.cliente.get("/api/modelo/info", headers=self.headers).status_code, 200)

    def test_clave_no_configurada_deshabilita_modelo(self):
        with patch("api.security.API_KEY", ""), patch.object(servicio, "predecir_con_sagemaker") as invocar:
            respuesta = self.cliente.post("/api/modelo/predecir", json={"glosa": "PISCO"})
            self.assertEqual(respuesta.status_code, 503)
            invocar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
