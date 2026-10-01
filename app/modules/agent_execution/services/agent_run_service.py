import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from app.modules.agent_execution.schemas.execution_events import FailedEvent
from app.modules.agent_execution.schemas.cancellation_response import CancellationResponse
from app.modules.agent_execution.repositories.agent_run_repository import TERMINAL


class AgentRunService:
    def __init__(self, registry, repository, policy, executors, resolver, lifecycle, profile_ids):
        self.registry, self.repository, self.policy = registry, repository, policy
        self.executors, self.resolver, self.lifecycle = executors, resolver, lifecycle
        self.profile_ids = set(profile_ids)

    def executor(self, definition):
        key = "hub_native" if definition.integration.type == "hub_native" else definition.integration.adapter_id
        if key not in self.executors:
            raise ValueError("No executor is registered for this agent.")
        if key == "openai_chat" and (
            definition.model_binding.type == "hub_per_run"
            or definition.capabilities.cancellation or definition.capabilities.status_query
        ):
            raise ValueError("openai_chat adapter requires fixed/managed models and has no cancellation/status API.")
        return self.executors[key]

    async def prepare(self, task, user_id):
        definition = await self.registry.get_executable_definition(task.agent_id)
        prepared = self.policy.prepare(definition, task)
        if (definition.model_binding.gateway_profile_id
                and definition.model_binding.gateway_profile_id not in self.profile_ids):
            raise ValueError("Agent gateway profile is not configured.")
        self.executor(definition)
        if prepared.model_ref:
            target = await self.resolver.resolve(prepared.model_ref)
            if not target.capabilities.streaming:
                raise ValueError("This agent requires a streaming model.")
        if definition.integration.type == "hub_native":
            health = await self.lifecycle.health(definition)
            if not health["ready"]:
                raise ValueError("Agent service is not ready.")
        now = datetime.now(UTC)
        await self.repository.create({
            "_id": prepared.run_id, "user_id": user_id, "agent_id": definition.id,
            "agent_version": definition.version, "definition": definition.model_dump(mode="json"),
            "model_ref": prepared.model_ref.model_dump() if prepared.model_ref else None,
            "status": "preparing", "cancel_requested": False, "created_at": now,
            "expires_at": now + timedelta(seconds=prepared.timeout_seconds),
        })
        return definition, prepared

    async def stream_prepared(self, definition, task):
        executor = self.executor(definition)
        sequence, terminal = 0, False
        await self.repository.update_active(task.run_id, {"status": "running"})
        stop = asyncio.Event()

        async def monitor():
            attempted = False
            while not stop.is_set():
                record = await self.repository.get(task.run_id)
                if record and record.get("cancel_requested") and not attempted:
                    try:
                        result = await executor.cancel(definition, task.run_id)
                        attempted = result.status != "not_found"
                        await self.repository.update_active(
                            task.run_id, {"cancel_delivery": result.status},
                        )
                    except Exception:
                        await self.repository.update_active(
                            task.run_id, {"cancel_delivery": "failed"},
                        )
                try:
                    await asyncio.wait_for(stop.wait(), 0.25)
                except TimeoutError:
                    pass

        monitor_task = asyncio.create_task(monitor())
        try:
            async with asyncio.timeout(task.timeout_seconds):
                async for event in executor.stream_run(definition, task):
                    sequence += 1
                    normalized = event.model_copy(update={"sequence": sequence})
                    if event.type in {"completed", "failed", "cancelled"}:
                        terminal = True
                        await self.repository.terminal(task.run_id, event.type)
                    yield normalized
                    if terminal:
                        return
        except asyncio.CancelledError:
            raise
        except Exception:
            terminal = True
            try:
                if definition.capabilities.cancellation:
                    await executor.cancel(definition, task.run_id)
            except Exception:
                pass
            await self.repository.terminal(task.run_id, "failed", remote_status="unconfirmed")
            yield FailedEvent(run_id=task.run_id, sequence=sequence + 1,
                              code="agent_run_failed", message="Agent execution failed or timed out.")
        finally:
            stop.set()
            monitor_task.cancel()
            await asyncio.gather(monitor_task, return_exceptions=True)
            if not terminal:
                try:
                    if definition.capabilities.cancellation:
                        await asyncio.shield(executor.cancel(definition, task.run_id))
                except Exception:
                    pass
                await asyncio.shield(self.repository.terminal(
                    task.run_id, "disconnected", remote_status="unconfirmed",
                ))

    async def get_owned(self, run_id, user_id):
        run = await self.repository.get(run_id, user_id)
        if run is None:
            raise LookupError("Run was not found.")
        return run

    async def cancel(self, run_id, user_id):
        run = await self.get_owned(run_id, user_id)
        if run["status"] in TERMINAL:
            status = run["status"] if run["status"] in {"completed", "failed", "cancelled"} else "failed"
            return CancellationResponse(run_id=run_id, status="already_terminal", terminal_status=status)
        from app.modules.agent_management.domain.agent_definition import AgentDefinition
        definition = AgentDefinition.model_validate(run["definition"])
        if not definition.capabilities.cancellation:
            return CancellationResponse(run_id=run_id, status="unsupported")
        await self.repository.request_cancel(run_id)
        # Deliver directly so cancellation works from a different Hub worker.
        result = await self.executor(definition).cancel(definition, run_id)
        if result.status == "not_found":
            return CancellationResponse(run_id=run_id, status="cancel_requested")
        return result
