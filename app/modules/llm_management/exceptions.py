# modules/llm_management/exceptions.py
class ModelActivationError(Exception):
    """所有跟啟動模型相關的自訂例外的共同基底"""


class PortAllocationError(ModelActivationError):
    pass


class UnsupportedOverrideKeysError(ModelActivationError):
    def __init__(self, unknown_keys: set[str]):
        self.unknown_keys = unknown_keys
        super().__init__(f"Unsupported override keys: {unknown_keys}")