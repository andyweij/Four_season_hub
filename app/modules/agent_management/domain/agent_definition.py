from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.modules.agent_execution.schemas.execution_request import ModelRef
from app.modules.agent_management.domain.enums import (
    AgentIntegrationType,
    AgentModelBindingType,
    AgentRuntimeType,
)


class DefinitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentCapabilities(DefinitionModel):
    """Hub 整合後實際能提供的能力；未知時保持 False。"""

    generation_parameters: bool = Field(default=False, strict=True)
    task_submission: bool = Field(default=False, strict=True)
    streaming: bool = Field(default=False, strict=True)

    # 表示能確認遠端工作停止，不只是關閉前端串流。
    cancellation: bool = Field(default=False, strict=True)

    # 表示能從 Agent API 查詢工作狀態。
    status_query: bool = Field(default=False, strict=True)

    # 表示有結構化來源，不能僅因回答有 URL 就設成 True。
    structured_sources: bool = Field(default=False, strict=True)


class AgentIntegration(DefinitionModel):
    type: AgentIntegrationType

    # 原生服務或 Adapter 使用的 Agent 任務 API 地址。
    # 不一定等於 Agent 的 UI 地址。
    endpoint: AnyHttpUrl | None = None

    # 指向 Hub 已註冊的 Adapter。
    # 這是識別字，不是可任意 import 的 Python 路徑。
    adapter_id: str | None = Field(default=None, min_length=1)

    # Third-party chat-task API model alias; not a Hub model reference.
    model_alias: str | None = Field(default=None, min_length=1)

    # 原生 Agent 使用；第三方契約版本由其 Adapter 管理。
    contract_version: str | None = None

    # Hub 呼叫 Agent 任務 API 所需的憑證識別。
    # 不是模型金鑰，也不是 Tavily 金鑰。
    credential_ref: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_integration(self) -> "AgentIntegration":
        if self.type == AgentIntegrationType.HUB_NATIVE:
            if self.endpoint is None:
                raise ValueError("hub_native requires endpoint")
            if self.contract_version != "1":
                raise ValueError("hub_native requires contract_version=1")
            if self.adapter_id is not None:
                raise ValueError("hub_native must not specify adapter_id")

        elif self.type == AgentIntegrationType.ADAPTER:
            if not self.adapter_id:
                raise ValueError("adapter requires adapter_id")
            if self.endpoint is None:
                raise ValueError("adapter requires endpoint")
            if self.contract_version is not None:
                raise ValueError(
                    "third-party contract belongs to its adapter"
                )

        else:
            if self.adapter_id is not None:
                raise ValueError(
                    "registration_only must not specify adapter_id"
                )
            if self.contract_version is not None:
                raise ValueError(
                    "registration_only has no execution contract"
                )

        return self


class AgentRuntime(DefinitionModel):
    type: AgentRuntimeType = AgentRuntimeType.EXTERNAL

    # Managed Docker image; per-agent environment is configured in Hub settings.
    # Volume/GPU mounts and rolling upgrades are not supported.
    image: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_runtime(self) -> "AgentRuntime":
        if self.type == AgentRuntimeType.DOCKER:
            if not self.image:
                raise ValueError("docker runtime requires image")
        elif self.image is not None:
            raise ValueError("external runtime must not specify image")

        return self


class AgentModelBinding(DefinitionModel):
    type: AgentModelBindingType

    # Hub 已登記的模型代理連線設定識別。
    # 之後包含代理地址、模型別名與代理金鑰的查找方式。
    # 不在這裡保存明文 Key。
    gateway_profile_id: str | None = Field(
        default=None,
        min_length=1,
    )

    # hub_per_run 的可選預設值；使用者可以選擇其他已授權模型。
    default_model_ref: ModelRef | None = None

    @model_validator(mode="after")
    def validate_binding(self) -> "AgentModelBinding":
        hub_modes = {
            AgentModelBindingType.HUB_PER_RUN,
            AgentModelBindingType.HUB_FIXED,
            AgentModelBindingType.MIXED,
        }

        if self.type in hub_modes and not self.gateway_profile_id:
            raise ValueError(
                "Hub model access requires gateway_profile_id"
            )

        if self.type != AgentModelBindingType.HUB_PER_RUN:
            if self.default_model_ref is not None:
                raise ValueError(
                    "default_model_ref only applies to hub_per_run"
                )

        if self.type == AgentModelBindingType.AGENT_MANAGED:
            if self.gateway_profile_id is not None:
                raise ValueError(
                    "agent_managed must not specify gateway_profile_id"
                )

        return self


class AgentDefinition(DefinitionModel):
    """Agent 定義，不包含目前的健康狀態或單次 run 狀態。"""

    id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)

    # 新登記預設不啟用。
    enabled: bool = Field(default=False, strict=True)

    integration: AgentIntegration
    runtime: AgentRuntime = Field(default_factory=AgentRuntime)
    model_binding: AgentModelBinding
    capabilities: AgentCapabilities = Field(
        default_factory=AgentCapabilities
    )

    @model_validator(mode="after")
    def validate_capabilities(self) -> "AgentDefinition":
        capabilities = self.capabilities

        if self.integration.type == AgentIntegrationType.REGISTRATION_ONLY:
            if any(
                (
                    capabilities.generation_parameters,
                    capabilities.task_submission,
                    capabilities.streaming,
                    capabilities.cancellation,
                    capabilities.status_query,
                    capabilities.structured_sources,
                )
            ):
                raise ValueError(
                    "registration_only has no task execution capabilities"
                )

        if not capabilities.task_submission:
            if capabilities.generation_parameters:
                raise ValueError("generation parameters require task submission")
            if any(
                (
                    capabilities.streaming,
                    capabilities.cancellation,
                    capabilities.status_query,
                    capabilities.structured_sources,
                )
            ):
                raise ValueError(
                    "execution capabilities require task_submission"
                )

        return self


class AgentCatalog(DefinitionModel):
    """Catalog 的格式驗證；載入與持久化稍後實作。"""

    schema_version: str = "1"
    agents: list[AgentDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_catalog(self) -> "AgentCatalog":
        if self.schema_version != "1":
            raise ValueError("unsupported catalog schema_version")

        ids = [agent.id for agent in self.agents]

        if len(ids) != len(set(ids)):
            raise ValueError("agent ids must be unique")

        return self