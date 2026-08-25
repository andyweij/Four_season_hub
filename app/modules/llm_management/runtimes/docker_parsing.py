from app.modules.llm_management.domain.model_instance import ModelRuntimeStatus


def extract_ports(container) -> tuple[int, int]:
    ports = container.attrs.get("NetworkSettings", {}).get("Ports") or {}
    for private_port_proto, bindings in ports.items():
        if not bindings:
            continue
        private_port = int(private_port_proto.split("/")[0])
        public_port = int(bindings[0]["HostPort"])
        return public_port, private_port
    return 0, 0


def classify_status(container) -> ModelRuntimeStatus:
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
