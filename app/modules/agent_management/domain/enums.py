from enum import StrEnum


class AgentIntegrationType(StrEnum):
    """Hub 如何提交任務與取得結果。"""

    # 遵循我們的 /v1/runs 契約。
    HUB_NATIVE = "hub_native"

    # 由 Hub 的 Adapter 轉換成第三方 API。
    ADAPTER = "adapter"

    # 只能登記與提供模型存取，尚無任務整合。
    REGISTRATION_ONLY = "registration_only"


class AgentRuntimeType(StrEnum):
    """Hub 是否控制 Agent 的執行程序。"""

    EXTERNAL = "external"
    DOCKER = "docker"


class AgentModelBindingType(StrEnum):
    """Agent 的模型如何指定與管理。"""

    # 每次任務可以選擇 Hub 模型。
    HUB_PER_RUN = "hub_per_run"

    # Agent 實例固定使用 Hub 的模型代理或模型別名。
    HUB_FIXED = "hub_fixed"

    # 模型 endpoint 與供應商金鑰由 Agent 自行管理。
    AGENT_MANAGED = "agent_managed"

    # 部分模型走 Hub，部分由 Agent 管理。
    MIXED = "mixed"