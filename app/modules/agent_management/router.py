from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from app.security.dependencies import CurrentUserDependency, require_roles
from app.security.models import CurrentUser
from app.modules.agent_management.exceptions import AgentManagementError
from app.modules.model_gateway.security.access_key_service import ProxyKeyRequest

router = APIRouter(tags=["Agents"])
Admin = Annotated[CurrentUser, Depends(require_roles("admin"))]


class EnableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


def public_definition(agent):
    return {
        "id": agent.id, "name": agent.name, "version": agent.version, "enabled": agent.enabled,
        "integration_type": agent.integration.type.value,
        "runtime_type": agent.runtime.type.value,
        "model_binding": agent.model_binding.type.value,
        "capabilities": agent.capabilities.model_dump(),
    }


@router.get("/agents")
async def agents(request: Request, user: CurrentUserDependency):
    return [public_definition(a) for a in await request.app.state.agent_services.registry.list_definitions()]


@router.get("/admin/agents/{agent_id}/health")
async def health(agent_id: str, request: Request, user: Admin):
    services = request.app.state.agent_services
    agent = await services.registry.get_definition(agent_id)
    return await services.lifecycle.health(agent)


@router.patch("/admin/agents/{agent_id}")
async def enable(agent_id: str, body: EnableRequest, request: Request, user: Admin):
    services = request.app.state.agent_services
    try:
        agent = await services.registry.get_definition(agent_id)
        if body.enabled:
            if agent.integration.type == "registration_only":
                raise ValueError("Registration-only agent cannot accept tasks.")
            services.runs.executor(agent)
            profile = agent.model_binding.gateway_profile_id
            if profile and profile not in services.runs.profile_ids:
                raise ValueError("Gateway profile is unavailable.")
            if agent.integration.type == "hub_native":
                if not services.access_keys.signing_key or len(services.access_keys.signing_key) < 32:
                    raise ValueError("Agent signing key is unavailable.")
                services.runs.executor(agent).headers(agent)
                if not (await services.lifecycle.health(agent))["ready"]:
                    raise ValueError("Agent is not ready.")
        return public_definition(await services.registry.set_enabled(agent_id, body.enabled))
    except (AgentManagementError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/admin/agents/{agent_id}/start")
async def start(agent_id: str, request: Request, user: Admin):
    services = request.app.state.agent_services
    try:
        return await services.lifecycle.start(await services.registry.get_definition(agent_id))
    except (ValueError, AgentManagementError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/admin/agents/{agent_id}/stop")
async def stop(agent_id: str, request: Request, user: Admin):
    services = request.app.state.agent_services
    try:
        definition = await services.registry.set_enabled(agent_id, False)
        return await services.lifecycle.stop(definition)
    except (ValueError, AgentManagementError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/agent-runs/{run_id}")
async def run_status(run_id: str, request: Request, user: CurrentUserDependency):
    try:
        run = await request.app.state.agent_services.runs.get_owned(run_id, user.subject)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    # Do not expose the internal definition, credentials or endpoints.
    return {k: run.get(k) for k in (
        "agent_id", "agent_version", "status", "created_at", "finished_at",
        "cancel_requested", "cancel_delivery", "remote_status",
    )} | {"run_id": run_id}


@router.post("/agent-runs/{run_id}/cancel")
async def cancel(run_id: str, request: Request, user: CurrentUserDependency):
    try:
        return await request.app.state.agent_services.runs.cancel(run_id, user.subject)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "Remote cancellation could not be confirmed.") from exc


@router.post("/admin/model-proxy/keys")
async def create_key(body: ProxyKeyRequest, request: Request, user: Admin):
    services = request.app.state.agent_services
    for ref in body.models.values():
        await services.gateway.resolver.resolve(ref)
    return await services.access_keys.create_proxy_key(body, user.subject)


@router.get("/admin/model-proxy/keys")
async def list_keys(request: Request, user: Admin):
    keys = await request.app.state.agent_services.access_keys.list_keys()
    return [{**item, "id": item["_id"]} for item in keys]


@router.delete("/admin/model-proxy/keys/{key_id}")
async def revoke_key(key_id: str, request: Request, user: Admin):
    if not await request.app.state.agent_services.access_keys.revoke_key(key_id):
        raise HTTPException(404, "Proxy key was not found.")
    return {"status": "revoked"}
