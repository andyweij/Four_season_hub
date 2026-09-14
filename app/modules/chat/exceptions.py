class ChatError(Exception):
    """chat 模組所有例外的共同基底類別。"""


class LlmInferenceError(ChatError):
    def __init__(self, model_name: str):
        self.model_name = model_name
        super().__init__(f"Model '{model_name}' is not running")


class ConversationAccessDeniedError(ChatError):
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        super().__init__(
            f"Conversation '{conversation_id}' not found or not owned by the caller"
        )