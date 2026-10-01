# Model Gateway Contract v1

## API

- POST /internal/v1/model/completions
  接受 CompletionRequest，回傳 CompletionResponse。
- POST /internal/v1/model/completions/stream
  串流契約於下一步定義。

## 責任

- Gateway 驗證執行憑證、run、模型與使用權限。
- Gateway 解析模型設定及供應商憑證。
- Agent 負責工具執行；Gateway 不執行 Tavily 等工具。
- 請求不得包含供應商金鑰或任意模型 endpoint。

## 訊息規則

- assistant 的 tool_calls 保存模型產生的呼叫 ID。
- tool 訊息使用 tool_call_id 對應先前呼叫。
- 再次呼叫模型前，每個工具呼叫都必須有對應結果。
- 工具失敗也必須提供工具結果，不能留下未配對呼叫。
- 工具配對與訊息順序由 Gateway 服務驗證。

## 能力與參數

- Gateway 使用伺服器端模型能力設定。
- 不支援工具呼叫的模型不得接受啟用工具的請求。
- 不支援的生成參數應明確拒絕，不默默忽略。
- max_tokens 表示輸出 token 上限。
- 模型 adapter 負責轉換供應商的參數名稱。

## 供應商狀態

- provider_state_ref 指向 Gateway 保存的原始供應商狀態。
- 必須綁定 run、模型與有效時間。
- 不得跨 run 或跨模型使用。
- Agent 不解讀或修改供應商原始狀態。
- 多程序部署時需要可共享的狀態保存方式。

## 逾時與取消

- Gateway 根據執行授權與剩餘期限限制模型呼叫。
- Agent 不得透過請求延長已核准的執行期限。
- 請求取消時，Gateway 應停止尚未完成的上游呼叫。


## 串流契約

- POST /internal/v1/model/completions/stream 回傳 SSE。
- 第一版串流端點只接受 tools=[]、tool_choice="none"。
- 工具決策使用非串流 completions 端點。
- 每次模型呼叫由 Gateway 產生新的 completion_id。
- sequence 在每次 completion 從 1 開始，嚴格遞增。
- 第一個事件是 started。
- content_delta 與 reasoning_delta 分別依序追加。
- completed、failed、cancelled 是互斥的終止事件。
- 終止事件之後不得再發送事件。
- SSE event 欄位等於事件 JSON 的 type。
- SSE id 使用 completion_id:sequence。
- v1 不支援串流續傳或事件重播。

## 統計與結束

- usage 表示這一次模型呼叫的統計。
- 不同 usage 更新不可直接相加，供應商可能傳回累計值。
- 未知 usage 保持 None。
- 供應商停止輸出後，adapter 應先讀取剩餘統計，再發出 completed。
- 無有效結束標記且連線意外中斷時，不得判定為成功。
- 串流取消與正常完成競態只能提交一個終止結果。

## 入口定位

- 本文件描述 Hub 自訂的內部模型契約。
- 第三方標準模型代理使用獨立的相容協定入口。
- 兩種入口共用 ModelResolver 與模型執行服務。
- 不將本文件的自訂事件直接當成標準模型 API 事件。