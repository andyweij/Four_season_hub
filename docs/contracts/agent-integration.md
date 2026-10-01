# Agent Integration

## Agent 定義、實例與執行

- AgentDefinition 描述整合設定、版本及宣告能力。
- 服務健康狀態由 AgentInstance 管理。
- 單次工作狀態由 AgentRun 管理。
- enabled=false 表示不接受新工作，不代表停止服務。

## 任務整合

- hub_native 使用 Hub 的 agent-execution-v1 契約。
- adapter 使用第三方任務 API，由 Hub Adapter 轉換。
- registration_only 不提供聊天任務提交。
- 可設定模型 endpoint/API Key 不代表提供任務 API。
- Adapter 必須如實揭露串流、取消及查詢能力。

## 模型綁定

- hub_per_run：每次工作可指定已授權的 Hub 模型。
- hub_fixed：實例固定使用 Hub 模型代理設定。
- agent_managed：模型與供應商憑證由 Agent 自主管理。
- mixed：只有經過 Hub 的呼叫受 Hub 模型政策控制。
- hub_fixed 的模型由代理 profile 或 Agent 實例設定決定。
- 不在每次工作前修改共用 Agent 的全域模型設定。

## 部署管理

- external 不授權 Hub 控制 Agent 程序。
- docker 由 Runtime Adapter 管理程序生命週期。
- 任務整合方式與部署管理方式互相獨立。

## 憑證分類

- integration.credential_ref：Hub 呼叫 Agent 的任務 API。
- gateway_profile_id：Agent 使用 Hub 模型代理的設定。
- 供應商模型金鑰：由 Hub 或 Agent 按模型管理模式保存。
- 工具金鑰：由工具所屬服務管理，例如 Tavily。
- Catalog 不保存明文金鑰。

## 載入與啟用

- JSON schema 驗證不代表整合已就緒。
- 啟用前必須確認 Adapter、代理 profile 與憑證參照存在。
- 宣告能力必須經過整合測試確認。
- Agent 任務 API 地址由管理員設定，不接受聊天請求指定。

## Hub 通用任務

- AgentTaskRequest 是 Hub 內部任務格式。
- ExecutionRequest 是 hub_native 的外部請求格式。
- 第三方 Adapter 將通用任務轉成其服務要求的格式。
- Agent 模型管理模式決定任務是否允許指定模型。
- parameters 與 options 必須經過整合專屬驗證。
- 不支援的指定應明確拒絕，不默默忽略。

## 統一事件

- Hub 使用 ExecutionEvent 作為統一執行事件。
- 第三方不必直接提供此格式，由 Adapter 轉換。
- 沒有原生文字串流時，可以在完整回答後產生 text_delta。
- 不得虛構來源、思考內容或取消能力。
- started 表示已開始處理，不保證第三方工作已成功提交。
- 接受前的錯誤直接拋出；started 後的錯誤產生 failed。
- sequence 與單一終止事件仍須由執行流程保證。

## 工作識別

- Hub run_id 與第三方工作 ID 分開保存。
- 第三方 session ID 不等於單次工作 ID。
- 映射必須綁定 Agent 實例與工作所有權。
- 多程序部署時不能僅依靠記憶體保存映射。

## 取消

- cancel_requested 只代表已提出取消。
- 確認遠端停止後才記錄 cancelled。
- 不支援取消時可以停止觀看，但遠端狀態仍需追蹤。
- Hub 等待逾時不代表第三方工作已經停止。