import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
from app.modules.cloud_llm_management.domain.enums import CloudLLMProvider, CloudLLMStatus
from app.modules.cloud_llm_management.domain.endpoints import provider_base_url
from app.modules.cloud_llm_management.services.connection_probe import probe_connection
from app.modules.cloud_llm_management.services.cloud_llm_mgt_service import CloudLLMManagementService
from app.modules.cloud_llm_management.schemas.add_llm import AddLLM


def connection(provider=CloudLLMProvider.GEMINI, **values):
    return SimpleNamespace(
        provider=provider, base_url=values.get("base_url"), model_name=values.get("model_name", "gemini-test"),
        enabled=False, status=CloudLLMStatus.UNTESTED,
    )


class ProbeTests(unittest.IsolatedAsyncioTestCase):
    async def test_gemini_without_endpoint_uses_default_and_no_generation(self):
        requests = []
        def response(request):
            requests.append(request)
            self.assertEqual(request.method, "GET")
            self.assertEqual(str(request.url), "https://generativelanguage.googleapis.com/v1beta/models/gemini-test")
            self.assertEqual(request.headers["x-goog-api-key"], "test-key")
            return httpx.Response(200, json={"name": "models/gemini-test", "supportedGenerationMethods": ["generateContent"]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as http:
            status, latency, _ = await probe_connection(http, connection(), "test-key")
        self.assertEqual(status, CloudLLMStatus.AVAILABLE)
        self.assertGreaterEqual(latency, 1)
        self.assertEqual(len(requests), 1)

    async def test_failure_statuses_and_no_key_in_message(self):
        for code, expected in [(401, "authentication_failed"), (403, "authentication_failed"),
                               (404, "model_not_found"), (429, "rate_limited"), (500, "unreachable")]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(code, json={"error": {"message": "sensitive-test-key"}})
            )) as http:
                status, _, message = await probe_connection(http, connection(), "sensitive-test-key")
                self.assertEqual(status, expected)
                self.assertNotIn("sensitive-test-key", message)

    async def test_openai_model_allowlist_and_custom_base(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"data": [{"id": "configured-model"}]})
        )) as http:
            status, _, _ = await probe_connection(http, connection(
                CloudLLMProvider.OPENAI_COMPATIBLE, model_name="configured-model", base_url="https://example.com/v1/"
            ), "key")
            self.assertEqual(status, "available")
            status, _, _ = await probe_connection(http, connection(
                CloudLLMProvider.OPENAI_COMPATIBLE, model_name="missing-model"
            ), "key")
            self.assertEqual(status, "model_not_found")

    async def test_probe_saves_result_without_enabling_connection(self):
        item = connection()
        repository = SimpleNamespace(get_by_id=AsyncMock(return_value=item),
            get_credential=AsyncMock(return_value=object()), update=AsyncMock())
        service = CloudLLMManagementService(repository, SimpleNamespace(decrypt=lambda value: "key"))
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:
            httpx.Response(200, json={"name": "models/gemini-test", "supportedGenerationMethods": ["generateContent"]})
        )) as http:
            result = await service.test("conn_test", http)
        self.assertEqual(result["status"], "available")
        self.assertFalse(result["enabled"])
        self.assertIsNotNone(item.last_tested_at)
        repository.update.assert_awaited_once_with(item)

    def test_payload_accepts_missing_gemini_endpoint(self):
        request = AddLLM(name="Gemini", provider="gemini", model_name="gemini-test", api_key="key")
        self.assertIsNone(request.base_url)
        self.assertEqual(provider_base_url(request.provider, request.base_url),
                         "https://generativelanguage.googleapis.com/v1beta")


    async def test_invalid_parameter_is_not_reported_as_bad_key(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:
            httpx.Response(400, json={"error": {"status": "INVALID_ARGUMENT", "message": "secret-value"}})
        )) as http:
            status, _, message = await probe_connection(http, connection(), "secret-value")
        self.assertNotEqual(status, "authentication_failed")
        self.assertIn("HTTP 400", message)
        self.assertIn("INVALID_ARGUMENT", message)
        self.assertNotIn("secret-value", message)

    async def test_google_invalid_key_reason_is_reported_as_auth_failure(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:
            httpx.Response(400, json={"error": {"status": "INVALID_ARGUMENT",
                "details": [{"reason": "API_KEY_INVALID", "metadata": {"key": "secret-value"}}]}})
        )) as http:
            status, _, message = await probe_connection(http, connection(), "secret-value")
        self.assertEqual(status, "authentication_failed")
        self.assertIn("API_KEY_INVALID", message)
        self.assertNotIn("secret-value", message)

    async def test_editing_model_invalidates_old_success(self):
        from app.modules.cloud_llm_management.schemas.update_cloud_llm_request import UpdateCloudLLMRequest
        item = connection()
        item.status, item.enabled = CloudLLMStatus.AVAILABLE, True
        item.last_tested_at, item.last_latency_ms = "old", 20
        repository = SimpleNamespace(get_by_id=AsyncMock(return_value=item),
                                     update=AsyncMock(return_value=item))
        service = CloudLLMManagementService(repository, SimpleNamespace())
        updated = await service.update("conn_test", UpdateCloudLLMRequest(model_name="different-model"))
        self.assertEqual(updated.model_name, "different-model")
        self.assertEqual(updated.status, "untested")
        self.assertIsNone(updated.last_tested_at)
        self.assertIsNone(updated.last_latency_ms)
