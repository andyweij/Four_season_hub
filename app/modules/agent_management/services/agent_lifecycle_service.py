import asyncio
import json
from urllib.parse import urlparse


class AgentLifecycleService:
    def __init__(self, http_client, docker_client, network, runs, service_token=None, environment=None):
        self.http, self.docker = http_client, docker_client
        self.network, self.runs = network, runs
        self.service_token = service_token
        self.environment = environment or {}

    async def health(self, definition):
        if definition.integration.type != "hub_native":
            return {"ready": None, "status": "not_probed"}
        try:
            response = await self.http.get(
                str(definition.integration.endpoint).rstrip("/") + "/health/ready", timeout=3,
            )
            data = response.json()
            ready = (response.status_code == 200 and data.get("contract_version") == "1"
                     and data.get("agent_version") == definition.version)
            return {"ready": ready, "status": "ready" if ready else "unavailable"}
        except Exception:
            return {"ready": False, "status": "unreachable"}

    def name(self, definition):
        return f"fsh-agent-{definition.id}"

    async def start(self, definition):
        if definition.runtime.type != "docker":
            raise ValueError("External services must be started by their owner.")
        if self.docker is None:
            raise ValueError("Docker runtime is unavailable.")
        def launch():
            import docker
            try:
                container = self.docker.containers.get(self.name(definition))
                if container.labels.get("fsh.agent.id") != definition.id:
                    raise ValueError("Container is not managed by this Hub.")
                if container.status != "running":
                    container.start()
                return container.id
            except docker.errors.NotFound:
                env = dict(self.environment.get(definition.id, {}))
                if definition.integration.type == "hub_native":
                    if not self.service_token:
                        raise ValueError("Agent service token is not configured.")
                    env["APP_SERVICE_TOKEN"] = self.service_token
                container = self.docker.containers.run(
                    definition.runtime.image, name=self.name(definition), detach=True,
                    network=self.network, environment=env,
                    labels={"fsh.agent.id": definition.id}, mem_limit="1g",
                    cap_drop=["ALL"], security_opt=["no-new-privileges:true"],
                    extra_hosts={"host.docker.internal": "host-gateway"},
                )
                return container.id
        return {"container_id": await asyncio.to_thread(launch)}

    async def stop(self, definition):
        if definition.runtime.type != "docker" or self.docker is None:
            raise ValueError("Only managed Docker agents can be stopped.")
        if await self.runs.active_for_agent(definition.id):
            raise ValueError("Agent has active runs; disable and drain it before stopping.")
        def stop():
            container = self.docker.containers.get(self.name(definition))
            if container.labels.get("fsh.agent.id") != definition.id:
                raise ValueError("Container is not managed by this Hub.")
            container.stop(timeout=15)
        await asyncio.to_thread(stop)
        return {"status": "stopped"}
