# 去掉 Dify → 纯 Python Agent 方案 迁移计划

## 背景

当前架构是 Dify (编排层) + Python FastAPI (业务层)，两者都在做 LLM 意图分类，Dify 本质只是个 HTTP 代理 + 模板格式化，去掉后几乎零损失。

## 现状分析

### 5 个 Dify 工作流及其 Python 对应

| Dify 文件 | 做的事 | Python 已有实现 |
|---|---|---|
| `dify_chatflow.yml` | 顶级意图分类 (customer/enterprise/student) → 转发到子Agent | **缺失** — 需新建统一入口 |
| `dify_customer_workflow.yml` | 客服意图分类(8类) → 调用 `/api/customer/chat` | `POST /api/customer/chat` → `CustomerServiceAgent.route_intent()` |
| `dify_enterprise_workflow.yml` | 企业意图分类(7类) → 调用 `/api/enterprise/chat` 等 | `POST /api/enterprise/chat` → `EnterpriseAgent.route_intent()` |
| `dify_student_workflow.yml` | 学生意图分类(6类) → 调用 `/api/student/chat` 等 | `POST /api/student/chat` → `StudentAgent.route_intent()` |
| `dify_approval_workflow.yml` | 查待审批 → LLM提取参数 → 执行审批 | `GET/POST /api/enterprise/approvals/*` |

### 已有 LLM 调用能力 (`utils/llm_client.py`)

- `llm.chat(system_prompt, user_message)` — 单轮对话
- `llm.classify_intent(user_input, intents_dict)` — 意图分类
- `llm.extract_info(user_input, fields_list)` — 结构化信息提取
- `llm.generate_report(report_type, data)` — 报告生成
- 支持 OpenAI 兼容接口 (DeepSeek/GPT/通义千问等)

### 已有 3 个 Agent

- `agents/customer_service/agent.py` — `CustomerServiceAgent` (8种意图)
- `agents/enterprise/agent.py` — `EnterpriseAgent` (10种意图)
- `agents/student/agent.py` — `StudentAgent` (8种意图)

## 迁移步骤

### 第 1 步：新建统一对话入口

**新建文件 `api/chat_routes.py`**

新增 `/api/chat` 接口，替代 `dify_chatflow.yml` 的顶级路由功能：

- 接收 `{ "message": "用户输入" }` 
- 调用 LLM 做顶级意图分类：customer / enterprise / student
- 转发到对应 Agent 的 `route_intent()` 方法
- 返回统一格式 `{ "intent": "...", "response": "...", "agent": "..." }`

同时在 `/api/__init__.py` 中注册新路由。

### 第 2 步：删除 Dify 文件

删除这 5 个 YAML：
- `dify_chatflow.yml`
- `dify_customer_workflow.yml`  
- `dify_enterprise_workflow.yml`
- `dify_student_workflow.yml`
- `dify_approval_workflow.yml`

### 第 3 步：清理 Dify 相关引用

检查并清理代码中对 Dify 的引用：
- `api/student_routes.py` 中 `create_leave` 接口返回 `teacher_info` 的注释提到 "供Dify邮件通知用" — 改为 "供邮件通知用"
- 其他可能的 Dify 引用

### 第 4 步：添加 Chat UI (可选但建议)

纯 API 模式对用户不友好，建议加一个简单的 Web 界面：

**方案 A — Gradio (推荐，一行代码)**
```python
import gradio as gr
# 直接对接 /api/chat
```

**方案 B — 纯 HTML/JS 单页**
在 `static/index.html` 放一个聊天界面，调用 `/api/chat`

### 第 5 步：验证测试

启动服务后验证：
1. `POST /api/chat { "message": "我想了解新加坡留学" }` → 路由到 customer agent
2. `POST /api/chat { "message": "帮我查今天的日报" }` → 路由到 enterprise agent
3. `POST /api/chat { "message": "我最近压力很大" }` → 路由到 student agent
4. 审批流程走通：`GET /api/enterprise/approvals/pending` → `POST /api/enterprise/approvals/{id}/approve`

## 涉及文件清单

| 操作 | 文件 |
|---|---|
| 新建 | `api/chat_routes.py` |
| 修改 | `api/__init__.py` — 注册新路由 |
| 修改 | `api/student_routes.py` — 清理 Dify 注释 |
| 删除 | `dify_chatflow.yml` |
| 删除 | `dify_customer_workflow.yml` |
| 删除 | `dify_enterprise_workflow.yml` |
| 删除 | `dify_student_workflow.yml` |
| 删除 | `dify_approval_workflow.yml` |
| 可选新建 | `static/index.html` — Chat UI |
