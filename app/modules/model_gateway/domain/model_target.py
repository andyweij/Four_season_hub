from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ModelCapabilities:
    """描述 Gateway 能提供的能力；未知能力使用保守預設。"""

    streaming: bool = False
    tool_calling: bool = False
    reasoning: bool = False
    reasoning_effort: bool = False


@dataclass(frozen=True)
class ModelTarget:
    """Hub 內部使用，不直接序列化成 API 回覆。"""

    source: Literal["local", "cloud"]

    # 本地為模型識別；雲端為連線識別。
    id: str

    # 實際送給供應商的模型名稱。
    model_name: str

    provider: Literal["openai_compatible", "gemini"]

    # 由供應商 adapter 解讀的 API 根地址。
    # Gemini 使用預設服務時可以沒有自訂地址。
    base_url: str | None

    capabilities: ModelCapabilities

    # 包含輸入與輸出的上下文上限；未知時使用 None。
    max_context_tokens: int | None = None

    # 僅保存憑證查找識別，不保存解密後的 API Key。
    credential_ref: str | None = None