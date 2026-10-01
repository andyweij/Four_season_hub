# Agent Execution Contract v1

## 範圍

- 支援文字輸入。
- Hub 負責使用者權限、歷史訊息、模型授權與永久執行紀錄。
- Agent 負責執行流程、工具呼叫與串流事件。
- 模型與工具金鑰不得出現在請求 body 或事件中。
- 本契約適用於 hub_native Agent。
- 第三方 Agent 透過 Adapter 接入，不要求採用本契約。
- ExecutionRequest 是原生服務請求，不是所有 Agent 的通用任務模型。
## API

- POST /v1/runs：接受 ExecutionRequest，回傳 SSE。
- GET /v1/runs/{run_id}：查詢執行狀態。
- POST /v1/runs/{run_id}/cancel：要求取消工作。

## 事件規則

- sequence 從 1 開始，同一次 run 嚴格遞增。
- 第一個事件是 started。
- text_delta 與 reasoning_delta 依序追加。
- sources 是截至目前的完整清單，接收方取代舊清單。
- completed、failed、cancelled 是互斥的終止事件。
- 終止事件之後不得再產生事件。
- SSE 的 event 欄位必須等於 JSON 的 type。
- SSE 的 id 使用 run_id:sequence。
- v1 不支援斷線續傳或事件重播。

## 重複請求

- 同一 run_id 不得再次啟動新工作。
- 重複提交回傳 HTTP 409。
- v1 不自動重新執行中斷的工作。

## 取消與斷線

- cancel 表示提出取消要求，不代表工作已停止。
- Agent 確認停止後才產生 cancelled。
- 已終止的工作維持原本結果。
- 正常完成與取消同時發生時，只能提交一個終止狀態。
- Hub 與 Agent 串流連線中斷時，Agent 應取消未完成工作。
- Hub 未收到終止事件時，不得把工作判定為完成。

## 錯誤

- 接受執行前的驗證錯誤使用 HTTP 錯誤回應。
- started 之後的執行錯誤使用 failed 事件。
- 對外錯誤訊息不得包含金鑰、Authorization header
  或原始供應商請求內容。

## 時限

- timeout_seconds 是 Agent 執行的整體時限。
- Agent 可以套用更嚴格的服務端限制。
- 所有子模型呼叫與搜尋必須遵守剩餘執行時間。
