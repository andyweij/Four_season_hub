import docker
from docker.errors import NotFound

from app.modules.llm_management.domain.enums import ModelRuntimeStatus, ComponentType
from app.modules.llm_management.runtimes.labels import HUB_OWNER_VALUE, MANAGED_BY_LABEL, COMPONENT_LABEL
from app.modules.llm_management.schemas.model_instance import ManagedInstance


class DockerCompatRuntimeInspector:
    def __init__(
            self,
            base_url: str,
    ):
        self.base_url = base_url
        self.client = docker.DockerClient(base_url=base_url)

    def get_status(self, container_name: str) -> ModelRuntimeStatus:
        try:
            container = self.client.containers.get(container_name)
        except NotFound:
            return ModelRuntimeStatus.NOT_INSTALLED

        if container.status == "running":
            health = container.attrs.get("State", {}).get("Health", {}).get("Status")
            if health == "unhealthy":
                return ModelRuntimeStatus.UNHEALTHY
            return ModelRuntimeStatus.READY

        if container.status == "created":
            return ModelRuntimeStatus.INSTALLED
        if container.status == "exited":
            return ModelRuntimeStatus.STOPPED

        return ModelRuntimeStatus.UNKNOWN

    def list_hub_containers(
            self,
            component: ComponentType | None = None,
    ) -> list[ManagedInstance]:
        label_filters = [f"{MANAGED_BY_LABEL}={HUB_OWNER_VALUE}"]

        if component is not None:
            label_filters.append(f"{COMPONENT_LABEL}={component}")
        containers = self.client.containers.list(all=True, filters={"label": label_filters})

        return [ManagedInstance(
            id=container.id,
            name=container.name,
            component=ComponentType(container.labels[COMPONENT_LABEL]),
            status=self._classify_status(container),
            public_port=self._extract_ports(container)[0],
            private_port=self._extract_ports(container)[1],
        ) for container in containers]

    @staticmethod
    def _extract_ports(container) -> tuple[int, int]:
        ports = container.attrs.get("NetworkSettings", {}).get("Ports") or {}
        for private_port_proto, bindings in ports.items():
            if not bindings:
                continue
            private_port = int(private_port_proto.split("/")[0])
            public_port = int(bindings[0]["HostPort"])
            return public_port, private_port
        return 0, 0

    @staticmethod
    def _classify_status(container) -> ModelRuntimeStatus:
        if container.status == "running":
            health = container.attrs.get("State", {}).get("Health", {}).get("Status")
            if health == "unhealthy":
                return ModelRuntimeStatus.UNHEALTHY
            return ModelRuntimeStatus.READY
        if container.status == "created":
            return ModelRuntimeStatus.INSTALLED
        if container.status == "exited":
            return ModelRuntimeStatus.STOPPED
        return ModelRuntimeStatus.UNKNOWN
