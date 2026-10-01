from app.modules.agent_execution.schemas.execution_events import (
    StartedEvent, TextDeltaEvent, CompletedEvent,
)
from app.modules.agent_execution.schemas.cancellation_response import CancellationResponse


class OpenAIChatAgentExecutor:
    """Adapter for agents exposing a non-streaming OpenAI chat task API."""
    def __init__(self, http_client, credentials=None):
        self.http = http_client
        self.credentials = credentials or {}

    async def stream_run(self, definition, request):
        if definition.model_binding.type not in {"agent_managed", "hub_fixed", "mixed"}:
            raise ValueError("This adapter cannot select models per task.")
        if definition.capabilities.cancellation or definition.capabilities.status_query:
            raise ValueError("This adapter has no remote cancellation or status API.")
        yield StartedEvent(run_id=request.run_id, sequence=1)
        token = self.credentials.get(definition.integration.credential_ref)
        if definition.integration.credential_ref and not token:
            raise ValueError("Agent task credential is unavailable.")
        payload = {
            "model": definition.integration.model_alias or "agent",
            "messages": [m.model_dump() for m in request.messages], "stream": False,
        }
        if request.parameters:
            payload.update(request.parameters.model_dump(exclude_none=True))
        response = await self.http.post(
            str(definition.integration.endpoint), json=payload,
            headers={"Authorization": f"Bearer {token}"} if token else {},
            timeout=request.timeout_seconds,
        )
        if response.is_error:
            raise ValueError("Third-party agent task request failed.")
        data = response.json()
        content = data["choices"][0]["message"].get("content")
        if not isinstance(content, str):
            raise ValueError("Third-party agent did not return text.")
        if content:
            yield TextDeltaEvent(run_id=request.run_id, sequence=2, content=content)
        yield CompletedEvent(run_id=request.run_id, sequence=3,
                             finish_reason=data["choices"][0].get("finish_reason"))

    async def cancel(self, definition, run_id):
        return CancellationResponse(run_id=run_id, status="unsupported")
