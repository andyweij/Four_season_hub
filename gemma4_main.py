"""
與此專案無關
"""
import json
import base64
import fitz  # PyMuPDF
import requests
from pathlib import Path

# ===== llama.cpp 伺服器設定 =====
ENDPOINT = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "gemma4:26b"  # 與你 llama-server 載入或映射的別名一致即可

ITEM = "9.鋼軌伸縮接頭養護情形-伸縮接頭(EJ)檢查紀錄表"
LOCATION = "桃園"
TABLE_NAME = "伸縮接頭(EJ)檢查紀錄表"

INPUT_FOLDER = f"D:\\workspace\\鐵道局\\{ITEM}\\{LOCATION}"
OUTPUT_FOLDER = f"D:\\workspace\\鐵道局\\ocr_results\\gemma4-ocr\\{ITEM}\\{LOCATION}"

ROLE_PROMPT = f"""
# Role (角色定位)
你是一名專業的 Document OCR (光學字元辨識) 與資料結構化專家。

# Task (任務說明)
1. 請依序辨識上傳的影像文件，並將「{TABLE_NAME}」中，下面[指定]欄位與對應填寫值完整擷取。
2. 重複的數值，也必須分開列出。        
"""

PROMPT = {}
PROMPT["9.鋼軌伸縮接頭養護情形-伸縮接頭(EJ)檢查紀錄表"] = """
1. 50N or UIC60：鋼軌伸縮滑距範圍為120±62.5mm。
2. 50N-UIC60：鋼軌伸縮滑距範圍為125.5±75mm。
## 指定欄位：(呈現範例)
- EJ類別：50N
- 滑距(軌側；尖軌；受軌)
    -尖軌(左)：-5
    -受軌(左)：-10
    -尖軌(右)：-5
    -受軌(右)：-10
"""

Path(OUTPUT_FOLDER).mkdir(exist_ok=True, parents=True)

headers = {
    "Content-Type": "application/json"
}


def pdf_to_base64_images(pdf_path: Path, dpi: int = 200) -> list[str]:
    """將 PDF 的每一頁渲染為 PNG 並轉成 Base64 字串"""
    base64_images = []
    doc = fitz.open(pdf_path)
    zoom = dpi / 72  # 72 是 PDF 預設 DPI
    matrix = fitz.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        img_bytes = pix.tobytes("png")
        b64_str = base64.b64encode(img_bytes).decode("utf-8")
        base64_images.append(b64_str)
    doc.close()
    return base64_images


pdf_files = sorted(Path(INPUT_FOLDER).glob("*.pdf"))
print(f"找到 {len(pdf_files)} 個 PDF 檔案\n")

for i, pdf_path in enumerate(pdf_files, 1):
    file_name = pdf_path.stem
    print(f"[{i}/{len(pdf_files)}] 處理中: {pdf_path.name} ...")

    try:
        # 1. 將 PDF 轉為 Base64 圖片列表
        b64_images = pdf_to_base64_images(pdf_path, dpi=200)
        final_prompt = ROLE_PROMPT + "\n" + PROMPT.get(ITEM, "")

        # 2. 組裝 OpenAI 相容的多模態訊息結構
        user_content = []
        for img_b64 in b64_images:
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}"
                }
            })

        user_content.append({
            "type": "text",
            "text": final_prompt
        })

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            "temperature": 0.1,  # 抽取欄位建議保持低隨機性
            "max_tokens": 2048
        }

        # 3. 發送請求至本地 llama.cpp 服務
        response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=300)

        if response.status_code != 200:
            print(f"  失敗: {response.status_code} {response.text}")
            continue

        result = response.json()

        # 4. 解析標準 OpenAI Chat Completion 格式回傳
        output_text = result["choices"][0]["message"]["content"]

        # 儲存結果
        json_path = Path(OUTPUT_FOLDER) / f"{file_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        txt_path = Path(OUTPUT_FOLDER) / f"{file_name}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(output_text)

        print(f"  完成! 已存至 {json_path.name} / {txt_path.name}")

    except Exception as e:
        print(f"  發生錯誤: {e}")
        continue

print("\n===== 全部處理完成 =====")
