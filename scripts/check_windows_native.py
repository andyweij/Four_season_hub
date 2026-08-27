"""
手動驗證 WindowsNativeRuntimeInspector 是否能正確掃到本機正在跑的模型 process。

用法:
    uv run python scripts/check_windows_native.py <model_base_path> [--host 127.0.0.1]

範例:
    uv run python scripts/check_windows_native.py D:\\workspace\\models
"""
import argparse
import asyncio
import sys
from pathlib import Path

# 讓腳本能在不安裝套件的情況下直接 import app.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.llm_management.runtimes.windows_native import (  # noqa: E402
    WindowsNativeRuntimeInspector,
)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_base_path", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    inspector = WindowsNativeRuntimeInspector(
        model_base_path=args.model_base_path,
        health_host=args.host,
    )

    print(f"[1] 掃描 model_base_path={inspector.model_base_path} 底下的 process ...")
    instances = await inspector.list_running_instances()

    if not instances:
        print("    沒找到任何符合的 process。請確認:")
        print("    - model_base_path 是否跟 process 啟動參數裡的模型路徑前綴一致")
        print("    - process 是否用目前這個使用者權限可讀取到 cmdline（psutil.AccessDenied 會被跳過）")
        return

    for instance in instances:
        print(
            f"    pid={instance.id:<8} name={instance.name:<40} "
            f"status={instance.status:<12} port={instance.public_port}"
        )

    print("\n[2] 針對每個抓到的 instance，重複用 get_instance()/get_status() 驗證一致性 ...")
    for instance in instances:
        again = await inspector.get_instance(instance.name)
        status = await inspector.get_status(instance.name)
        ok = again is not None and again.id == instance.id and status == instance.status
        print(f"    name={instance.name:<40} get_instance/get_status 一致: {ok}")

    print("\n[3] 驗證查不存在的名稱時回傳 None / NOT_INSTALLED ...")
    missing = await inspector.get_instance("__definitely_not_a_real_model__")
    missing_status = await inspector.get_status("__definitely_not_a_real_model__")
    print(f"    get_instance -> {missing!r}, get_status -> {missing_status!r}")


if __name__ == "__main__":
    asyncio.run(main())
