class ThinkTagParser:
    """Splits a raw streamed text into (is_thinking, text) segments delimited by
    <think>...</think> tags, for models (e.g. Qwen3) that emit thinking content
    inline in `content` instead of a separate `reasoning_content` field.

    Stateful across chunks: a tag may be split across two stream chunks, so a
    trailing partial tag is held back in an internal buffer until it either
    completes or is proven not to be a tag.
    """

    _OPEN_TAG = "<think>"
    _CLOSE_TAG = "</think>"

    def __init__(self):
        self._in_thinking = False
        self._buffer = ""

    def feed(self, text: str) -> list[tuple[bool, str]]:
        self._buffer += text
        segments: list[tuple[bool, str]] = []

        while True:
            tag = self._CLOSE_TAG if self._in_thinking else self._OPEN_TAG
            idx = self._buffer.find(tag)
            if idx == -1:
                break
            if idx > 0:
                segments.append((self._in_thinking, self._buffer[:idx]))
            self._buffer = self._buffer[idx + len(tag):]
            self._in_thinking = not self._in_thinking

        hold_back = self._partial_tag_suffix_len(self._buffer)
        emit_len = len(self._buffer) - hold_back
        if emit_len > 0:
            segments.append((self._in_thinking, self._buffer[:emit_len]))
            self._buffer = self._buffer[emit_len:]
        return segments

    def flush(self) -> list[tuple[bool, str]]:
        if not self._buffer:
            return []
        segments = [(self._in_thinking, self._buffer)]
        self._buffer = ""
        return segments

    @classmethod
    def _partial_tag_suffix_len(cls, buffer: str) -> int:
        max_overlap = 0
        for tag in (cls._OPEN_TAG, cls._CLOSE_TAG):
            for i in range(min(len(tag) - 1, len(buffer)), 0, -1):
                if buffer.endswith(tag[:i]):
                    max_overlap = max(max_overlap, i)
                    break
        return max_overlap
