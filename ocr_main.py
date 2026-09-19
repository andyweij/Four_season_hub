"""
與此專案無關
"""
import time
import json
import requests
from pathlib import Path

# ===== 設定 =====
ENDPOINT = "https://eastus.api.cognitive.microsoft.com"
API_KEY = "b1d60743b5fe4540bbe7d9f76aa65123"
API_VERSION = "2024-11-30"
MODEL_ID = "prebuilt-read"  # 可換成 prebuilt-layout
ITEM = "1.焊口焊接作業-熱劑焊接作業自主檢查表"
LOCATION = "驗證用"
# LOCATION = "八堵"
# LOCATION = "桃園"
INPUT_FOLDER = f"D:\\workspace\\鐵道局\\{ITEM}\\{LOCATION}"  # PDF所在資料夾
OUTPUT_FOLDER = f"D:\\workspace\\鐵道局\\ocr_results\\azure-doc\\{ITEM}\\{LOCATION}"  # 結果輸出資料夾

ANALYZE_URL = f"{ENDPOINT}/documentintelligence/documentModels/{MODEL_ID}:analyze?api-version={API_VERSION}"

# ===== 建立輸出資料夾 =====
Path(OUTPUT_FOLDER).mkdir(exist_ok=True, parents=True)

# ===== 找出資料夾內所有 PDF =====
pdf_files = sorted(Path(INPUT_FOLDER).glob("*.pdf"))
print(f"找到 {len(pdf_files)} 個 PDF 檔案\n")

headers_post = {
    "Ocp-Apim-Subscription-Key": API_KEY,
    "Content-Type": "application/pdf"
}
headers_get = {
    "Ocp-Apim-Subscription-Key": API_KEY
}

# ===== 逐一處理 =====
for i, pdf_path in enumerate(pdf_files, 1):
    file_name = pdf_path.stem  # 不含副檔名的檔名
    print(f"[{i}/{len(pdf_files)}] 處理中: {pdf_path.name} ...")

    try:
        # ---- Step 1: 送出分析請求 ----
        with open(pdf_path, "rb") as f:
            response = requests.post(ANALYZE_URL, headers=headers_post, data=f)

        if response.status_code != 202:
            print(f"  送出失敗: {response.status_code} {response.text}")
            continue

        operation_location = response.headers["Operation-Location"]

        # ---- Step 2: 輪詢結果 ----
        while True:
            poll_response = requests.get(operation_location, headers=headers_get)
            result = poll_response.json()
            status = result.get("status")

            if status == "succeeded":
                break
            elif status == "failed":
                print(f"  分析失敗: {result}")
                break

            time.sleep(2)

        if status != "succeeded":
            continue

        analyze_result = result["analyzeResult"]

        # ---- Step 3a: 存成 JSON(完整結構化資料) ----
        json_path = Path(OUTPUT_FOLDER) / f"{file_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # ---- Step 3b: 存成純文字檔(方便快速閱讀) ----
        txt_path = Path(OUTPUT_FOLDER) / f"{file_name}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(analyze_result["content"])

        print(f"  完成! 已存至 {json_path.name} / {txt_path.name}")

    except Exception as e:
        print(f"  發生錯誤: {e}")
        continue

print("\n===== 全部處理完成 =====")
