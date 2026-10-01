import logging
from time import perf_counter
from urllib.parse import quote
import httpx
from app.modules.cloud_llm_management.domain.endpoints import provider_base_url
from app.modules.cloud_llm_management.domain.enums import CloudLLMStatus as Status


logger = logging.getLogger(__name__)


async def probe_connection(http, connection, key):
    """Verify credentials/model metadata, without generating billable content.

    Metadata success does not guarantee generation quota or streaming/tool capability.
    Existing capability settings are preserved.
    """
    started = perf_counter()
    base = provider_base_url(connection.provider, connection.base_url)
    code, reason = None, None
    try:
        if connection.provider == "gemini":
            name = connection.model_name.removeprefix("models/")
            response = await http.get(base + "/models/" + quote(name, safe=""),
                                      headers={"x-goog-api-key": key}, timeout=15)
        else:
            response = await http.get(base + "/models", headers={"Authorization": f"Bearer {key}"}, timeout=15)
        code = response.status_code
        status = ({401: Status.AUTHENTICATION_FAILED, 403: Status.AUTHENTICATION_FAILED,
                   404: Status.MODEL_NOT_FOUND, 429: Status.RATE_LIMITED}).get(code, Status.UNREACHABLE)
        if connection.provider == "gemini" and not response.is_success:
            try:
                error = response.json().get("error", {})
                known_reasons = {"API_KEY_INVALID", "API_KEY_EXPIRED", "API_KEY_SERVICE_BLOCKED",
                                 "API_KEY_HTTP_REFERRER_BLOCKED", "API_KEY_IP_ADDRESS_BLOCKED",
                                 "SERVICE_DISABLED", "PERMISSION_DENIED", "INVALID_ARGUMENT",
                                 "UNAUTHENTICATED", "NOT_FOUND", "RESOURCE_EXHAUSTED"}
                details = error.get("details", [])
                reason = next((d.get("reason") for d in details if isinstance(d, dict)
                               and d.get("reason") in known_reasons), None)
                if reason is None and error.get("status") in known_reasons:
                    reason = error["status"]
                if code == 400 and reason in {"API_KEY_INVALID", "API_KEY_EXPIRED", "UNAUTHENTICATED"}:
                    status = Status.AUTHENTICATION_FAILED
            except (ValueError, AttributeError, TypeError):
                pass
        if response.is_success:
            data = response.json()
            if connection.provider == "gemini":
                valid = (data.get("name") == "models/" + name
                         and "generateContent" in data.get("supportedGenerationMethods", []))
            else:
                valid = any(m.get("id") == connection.model_name for m in data.get("data", []) if isinstance(m, dict))
            status = Status.AVAILABLE if valid else Status.MODEL_NOT_FOUND
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        status = Status.UNREACHABLE
    messages = {
        Status.AVAILABLE: "金鑰與模型資訊驗證成功；尚未測試生成額度。",
        Status.AUTHENTICATION_FAILED: "供應商拒絕金鑰或權限，請更新 API Key 並確認其專案與使用限制。",
        Status.MODEL_NOT_FOUND: "找不到模型或不支援文字生成，請填入實際的模型 ID。",
        Status.RATE_LIMITED: "供應商已達速率限制，請稍後重試。",
        Status.UNREACHABLE: "供應商模型資訊 API 無法使用，或回應格式不正確。",
    }
    message = messages[status]
    if code == 400 and reason == "INVALID_ARGUMENT":
        message = "供應商拒絕請求參數，請檢查模型 ID 與 Endpoint；此結果不足以判定 API Key 無效。"
    if status != Status.AVAILABLE and code is not None:
        message += f"（供應商 HTTP {code}" + (f" / {reason}" if reason else "") + "）"
    logger.info("Cloud metadata probe provider=%s status=%s upstream_http=%s reason=%s",
                connection.provider, status, code, reason)
    return status, max(1, round((perf_counter() - started) * 1000)), message
