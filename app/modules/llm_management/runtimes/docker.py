# runtimes/docker.py
import asyncio

import docker
from docker.errors import NotFound

from app.modules.llm_management.domain.model_instance import (
    ComponentType, ModelInstance, ModelRuntimeStatus,
)
from app.modules.llm_management.runtimes.docker_parsing import classify_status, extract_ports
from app.modules.llm_management.runtimes.labels import (
    COMPONENT_LABEL, HUB_OWNER_VALUE, MANAGED_BY_LABEL,
)
import logging

logger = logging.getLogger("app")


class DockerCompatRuntimeInspector:
    def __init__(self, client: docker.DockerClient):
        self.client = client

    async def get_status(self, container_name: str) -> ModelRuntimeStatus:
        return await asyncio.to_thread(self._get_status_sync, container_name)

    def _get_status_sync(self, container_name: str) -> ModelRuntimeStatus:
        try:
            container = self.client.containers.get(container_name)
        except NotFound:
            return ModelRuntimeStatus.NOT_INSTALLED
        return classify_status(container)

    async def list_running_instances(
            self, component: ComponentType | None = None,
    ) -> list[ModelInstance]:
        return await asyncio.to_thread(self._list_hub_containers_sync, component)

    async def stop_and_remove_instance(self, container_name: str) -> None:
        ...

    def _list_hub_containers_sync(self, component: ComponentType | None = None) -> list[ModelInstance]:
        label_filters = [f"{MANAGED_BY_LABEL}={HUB_OWNER_VALUE}"]
        if component is not None:
            label_filters.append(f"{COMPONENT_LABEL}={component}")
        containers = self.client.containers.list(all=True, filters={"label": label_filters})
        return [
            ModelInstance(
                id=c.id,
                name=c.name,
                component=ComponentType(c.labels[COMPONENT_LABEL]),
                status=classify_status(c),
                public_port=extract_ports(c)[0],
                private_port=extract_ports(c)[1],
            )
            for c in containers
        ]

    async def get_instance(self, container_name: str) -> ModelInstance | None:
        return await asyncio.to_thread(self._get_instance_sync, container_name)

    def _get_instance_sync(self, container_name: str) -> ModelInstance | None:
        try:
            container = self.client.containers.get(container_name)
        except NotFound:
            return None
        if container.labels.get(MANAGED_BY_LABEL) != HUB_OWNER_VALUE:
            return None
        return ModelInstance(
            id=container.id,
            name=container.name,
            component=ComponentType(container.labels[COMPONENT_LABEL]),
            status=classify_status(container),
            public_port=extract_ports(container)[0],
            private_port=extract_ports(container)[1],
        )
