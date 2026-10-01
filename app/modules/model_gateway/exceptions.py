class ModelResolutionError(ValueError):
    """模型解析錯誤；後續由 API 層轉成安全的錯誤回應。"""

    code = "model_resolution_failed"


class ModelNotFoundError(ModelResolutionError):
    code = "model_not_found"


class ModelNotReadyError(ModelResolutionError):
    code = "model_not_ready"


class ModelNotChatCapableError(ModelResolutionError):
    code = "model_not_chat_capable"


class ModelSourceNotImplementedError(ModelResolutionError):
    code = "model_source_not_implemented"