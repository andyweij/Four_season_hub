class llm_inference_exception(Exception):
    """Base class for exceptions in the llm_inference module."""
    pass


class UpstreamInferenceError(llm_inference_exception):
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Upstream inference error: {status_code} - {body}")