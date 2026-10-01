import json


async def read_sse(lines):
    """Parse complete SSE frames, including multiline data and CRLF."""
    data = []
    event = None
    size = 0
    async for line in lines:
        line = line.rstrip("\r\n")
        if not line:
            if data:
                yield event, "\n".join(data)
            data, event, size = [], None, 0
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if field == "event":
            event = value
        elif field == "data":
            size += len(value)
            if size > 2_000_000:
                raise ValueError("SSE frame exceeds size limit.")
            data.append(value)
    if data:
        yield event, "\n".join(data)


def encode_sse(event):
    data = event.model_dump(mode="json") if hasattr(event, "model_dump") else event
    return f"event: {data['type']}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
