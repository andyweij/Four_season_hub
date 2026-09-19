from typing import Literal

from pydantic import BaseModel


class VolumeMount(BaseModel):
    host: str
    container: str
    mode: Literal["ro", "rw"] = "rw"
