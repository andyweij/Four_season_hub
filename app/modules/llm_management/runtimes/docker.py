import docker
from docker.errors import NotFound

from app.modules.llm_management.domain.model_instance import ModelRuntimeStatus, ComponentType
from app.modules.llm_management.runtimes.labels import HUB_OWNER_VALUE, MANAGED_BY_LABEL, COMPONENT_LABEL
from app.modules.llm_management.domain.model_instance import ModelInstance
from app.modules.llm_management.runtimes.docker_parsing import extract_ports, classify_status


class DockerCompatRuntimeInspector:
    def __init__(
            self,
            client: docker.DockerClient,
    ):
        self.client = client

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
    ) -> list[ModelInstance]:
        label_filters = [f"{MANAGED_BY_LABEL}={HUB_OWNER_VALUE}"]

        if component is not None:
            label_filters.append(f"{COMPONENT_LABEL}={component}")
        containers = self.client.containers.list(all=True, filters={"label": label_filters})

        return [ModelInstance(
            id=container.id,
            name=container.name,
            component=ComponentType(container.labels[COMPONENT_LABEL]),
            status=classify_status(container),
            public_port=extract_ports(container)[0],
            private_port=extract_ports(container)[1],
        ) for container in containers]
