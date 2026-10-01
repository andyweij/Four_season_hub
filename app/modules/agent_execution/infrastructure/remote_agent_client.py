import json
from pydantic import TypeAdapter
from app.infrastructure.streaming.sse import read_sse
from app.modules.agent_execution.schemas.execution_events import ExecutionEvent
from app.modules.agent_execution.schemas.execution_request import ExecutionRequest
from app.modules.agent_execution.schemas.cancellation_response import CancellationResponse


class RemoteAgentExecutor:
    def __init__(self, http_client, runs, access_keys, resolver, service_token, credentials=None):
        self.http, self.runs, self.access = http_client, runs, access_keys
        self.resolver, self.service_token = resolver, service_token
        self.credentials = credentials or {}
        self.event_adapter = TypeAdapter(ExecutionEvent)

    def headers(self, definition):
        token = self.credentials.get(definition.integration.credential_ref) or self.service_token
        if not token:
            raise ValueError("Agent service credential is not configured.")
        return {"Authorization": f"Bearer {token}"}

    async def stream_run(self, definition, request):
        run = await self.runs.get(request.run_id)
        target = await self.resolver.resolve(request.model_ref)
        token = self.access.issue_run_token(
            request.run_id, run["user_id"], request.model_ref, run["expires_at"],
        )
        body = ExecutionRequest(
            run_id=request.run_id, agent_version=definition.version, model_ref=request.model_ref,
            execution_mode="tool_calling" if target.capabilities.tool_calling else "search_first",
            messages=request.messages,
            parameters=request.parameters or {},
            limits={"timeout_seconds": request.timeout_seconds, **request.options},
        )
        headers = {**self.headers(definition), "X-Execution-Token": token}
        endpoint = str(definition.integration.endpoint).rstrip("/")
        last_sequence, started, terminal = 0, False, False
        async with self.http.stream("POST", f"{endpoint}/v1/runs",
                                    json=body.model_dump(mode="json"), headers=headers,
                                    timeout=request.timeout_seconds) as response:
            if response.is_error:
                raise ValueError(f"Agent rejected request (HTTP {response.status_code}).")
            async for name, text in read_sse(response.aiter_lines()):
                event = self.event_adapter.validate_json(text)
                if event.run_id != request.run_id or (name is not None and name != event.type):
                    raise ValueError("Agent returned an invalid event identity.")
                if terminal or event.sequence <= last_sequence:
                    raise ValueError("Agent returned invalid event ordering.")
                if not started and (event.type != "started" or event.sequence != 1):
                    raise ValueError("Agent must start with sequence 1.")
                started, last_sequence = True, event.sequence
                terminal = event.type in {"completed", "failed", "cancelled"}
                yield event
            if not terminal:
                raise ValueError("Agent disconnected without a terminal event.")

    async def cancel(self, definition, run_id):
        endpoint = str(definition.integration.endpoint).rstrip("/")
        response = await self.http.post(
            f"{endpoint}/v1/runs/{run_id}/cancel", headers=self.headers(definition), timeout=10,
        )
        if response.status_code == 404:
            return CancellationResponse(run_id=run_id, status="not_found")
        if response.is_error:
            raise ValueError("Agent cancellation request failed.")
        return CancellationResponse.model_validate(response.json())
