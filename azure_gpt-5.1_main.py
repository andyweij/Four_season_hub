"""
與此專案無關
"""

import base64
import requests
from pathlib import Path

# ===== 設定 =====
ENDPOINT = "https://iisikmoai.openai.azure.com/openai/v1/responses"
DEPLOYMENT_NAME = "gpt-5.1"  # 注意：有連字號
API_KEY = "6740d3eb8ea6414e84713fc1beeaf91a"

ITEM = "1.焊口焊接作業-熱劑焊接作業自主檢查表"
LOCATION = "驗證用"
TABLE_NAME = ITEM.split("-")[1]
INPUT_FOLDER = f"D:\\workspace\\鐵道局\\{ITEM}\\{LOCATION}"  # PDF所在資料夾
OUTPUT_FOLDER = f"D:\\workspace\\鐵道局\\ocr_results\\gpt-ocr-2\\{ITEM}\\{LOCATION}"

PROMPT = {}
ROLE_PROMPT = f"""
# Role (角色定位)
你正在執行逐格影像轉錄，只需存下[{TABLE_NAME}]表中的指定欄位資料，不是資料分析。
請嚴格遵守：
- 只抄錄圖片中實際可見的內容，不得推論、修正、補值或重新排列。
- 保持原始欄位由左至右、列由上至下的順序。
- 重複出現的欄名仍須分別抄錄，不得合併。
- 看不清楚時輸出 null，不得猜測。
- 先逐格轉錄，完成後再重新查看圖片，專門檢查：
"""
PROMPT[("15.平交道-平交道定期(每月)檢查表")] = """
## 表格解析規則
1. 焊口間距(軌縫)，包含四個尺寸，請依序由左到右、上到下呈現數值。例:25/20/25/25
2. 藥劑序號，是一張貼紙，上面會包含文字內容。
3. 鋼軌研磨為勾、叉兩種符號(V、X)。
4. 焊接點高度尺寸區間0.2mm-0.4mm

## 指定擷取欄位如下：
- 焊接點編號：
- 焊口間距(軌縫)mm：
- 藥劑序號：
- 預熱時間(秒)：
- 切口垂直度(度)：
- 剷除時間(秒)：
- 鋼軌研磨：
- 焊接點高度(1m)mm-北：
- 焊接點高度(1m)mm-南：
"""

PROMPT[("2.2.焊口列管及處置情形-鋼軌焊口檔案卡")] = """
## 指定擷取欄位如下：
- 焊接日期：
- 超音波檢測日期：
"""

PROMPT[("3.魚尾鈑裂縫瑕疵-夾膠絕緣檢查紀錄表")] = """
## 表格解析規則
1. 日期處理：
    - 日期格式可能會出現不同種類，需特別注意如下
    - 114.05.05；115/01/01；4/3；4/03
    - 可能包含人員簽名與日期+時間:王曉明 0515 1510
2. 檢視項目包含四項(接頭下沉、接頭拉(裂)開、配件狀況、噴泥)，每項皆有圈、叉兩種符號(O、X)，請依照圖片中實際出現的符號抄錄。
## 指定擷取欄位如下：
- 里程：
- 檢視項目：
    - 接頭下沉：
    - 接頭拉(裂)開：
    - 配件狀況：
    - 噴泥：
- 後續處置追蹤情形：
    - 預訂改善日期:
    - 改善完成日期(人員簽章)：
"""
PROMPT[("8.道岔養護情形-道岔檢查紀錄表")] = """
## 指定擷取欄位如下：
    - 檢測點位編號對應的軌距、水平、高低、方向
    - 檢測點位編號：1;2;3;3';4;4';5;5';6;6';7;7'
"""
PROMPT[("9.鋼軌伸縮接頭養護情形-伸縮接頭(EJ)檢查紀錄表")] = """
1. 50N or UIC60：鋼軌伸縮滑距範圍為120±62.5mm。
2. 50N-UIC60：鋼軌伸縮滑距範圍為125.5±75mm。
## 指定擷取欄位如下：
- EJ類別：50N
- 滑距(軌側；尖軌；受軌)
    -尖軌(左)：-30
    -受軌(左)：-10
    -尖軌(右)：5
    -受軌(右)：0
"""
PROMPT["10.路線巡查-路線巡查紀錄表"] = """
## 表格解析規則
1. 日期處理：
    - 日期格式：114.05.05
## 指定擷取欄位如下：
- 故障態樣：
- 量測人員簽章：
- 等級判定(A,B,C,D)：
- 預計改善日期：
- 改善完成日期：
"""
PROMPT["13.石碴檢查-噴泥處所控管總表"] = """
## 表格解析規則
1. 日期處理：
    - 日期格式：114.05.05
## 指定欄位如下：
預計改善日期：
實際改善日期：
"""

PROMPT["15.平交道-平交道定期(每月)檢查表"] = """
## 表格手寫符號解析規則：
1. 符號處理（Continuation Lines）：
    - 欄位中若出現貫穿或單純的垂直線（|）、折線（—|）或橫線，代表免填。
2. 日期處理：
    - 日期格式可能會出現不同種類，需特別注意如下
    - 114.05.05；115/01/01；4/3；4/03
    
## 指定欄位如下：    
- 檢查項目(10項)，對應以下欄位的資料
- 檢查缺失代號(1~13)：2
- 改善期限(1、2、3)：1
- 檢查人員/日期：114.5.5
- 改善人員/日期：114.5.5
"""
Path(OUTPUT_FOLDER).mkdir(exist_ok=True, parents=True)

headers = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

pdf_files = sorted(Path(INPUT_FOLDER).glob("*.pdf"))
print(f"找到 {len(pdf_files)} 個 PDF 檔案\n")

for i, pdf_path in enumerate(pdf_files, 1):
    file_name = pdf_path.stem
    print(f"[{i}/{len(pdf_files)}] 處理中: {pdf_path.name} ...")

    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode("utf-8")
        final_prompt = (
                ROLE_PROMPT + "\n" + PROMPT[ITEM])
        payload = {
            "model": DEPLOYMENT_NAME,  # <-- model放在body這裡
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": pdf_path.name,
                            "file_data": f"data:application/pdf;base64,{base64_pdf}"
                        },
                        {
                            "type": "input_text",
                            "text": final_prompt,
                        }
                    ]
                }
            ]
        }

        response = requests.post(ENDPOINT, headers=headers, json=payload)  # <-- 直接打ENDPOINT，不拼路徑

        if response.status_code != 200:
            print(f"  失敗: {response.status_code} {response.text}")
            continue

        result = response.json()

        output_text = ""
        for item in result.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        output_text += content.get("text", "")

        json_path = Path(OUTPUT_FOLDER) / f"{file_name}.json"
        # with open(json_path, "w", encoding="utf-8") as f:
        # json.dump(result, f, ensure_ascii=False, indent=2)

        txt_path = Path(OUTPUT_FOLDER) / f"{file_name}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(output_text)

        print(f"  完成! 已存至 {json_path.name} / {txt_path.name}")

    except Exception as e:
        print(f"  發生錯誤: {e}")
        continue

print("\n===== 全部處理完成 =====")
