from app.modules.llm_management.domain.enums import ComponentType

MANAGED_BY_LABEL = "com.fourseasonhub.managed-by"
COMPONENT_LABEL = "com.fourseasonhub.component"
HUB_OWNER_VALUE = "four-season-hub"


def build_label_filters(component: ComponentType | None = None) -> list[str]:
    filters = [f"{MANAGED_BY_LABEL}={HUB_OWNER_VALUE}"]
    if component is not None:
        filters.append(f"{COMPONENT_LABEL}={component}")
    return filters
