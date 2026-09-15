# runtimes/launch_args.py
from typing import Any

BOOLEAN_FLAGS_KEY = "boolean"
ENV_FLAGS_KEY = "env"


def build_config_args(args: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key, value in args.items():
        if key == BOOLEAN_FLAGS_KEY:
            result.extend(f"--{flag}" for flag in value)
        else:
            result.extend([f"--{key}", str(value)])
    return result


def parse_env_list(env: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in env:
        key, _, value = entry.partition("=")
        result[key] = value
    return result
