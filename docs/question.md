# 问题与修复记录

日期：2026-05-16 ~ 2026-05-17

---

# 第一部分：前端

## 1. 前端页面静态化 → 补齐缺失页面 + 修复数据流

**问题**：前端只有17个页面、36个API调用点，15个后端端点无前端对接，部分页面的CRUD数据流不通。

**解决**：

### 新建4个页面
| 页面 | 文件 | 对接端点 |
|---|---|---|
| 心理预警 | `static/js/pages/psychAlerts.js` | `GET/POST /api/student/psych-alert` |
| 报表中心 | `static/js/pages/reportsCenter.js` | 6个 `/api/reports/*` 端点，Tab切换 |
| 学生信息 | `static/js/pages/studentInfo.js` | `GET /api/student/info` |
| NL2SQL查询 | `static/js/pages/nl2sql.js` | `POST /api/enterprise/nl2sql` + `/update` |

### 增强2个页面
- **events.js**：每个活动卡片增加"查看报名"按钮，修复 `customer_id: 1` 硬编码
- **reports.js**：新增"语音转日报"按钮 → AI解析口述文本 → 预览 → 确认提交

### 修复6个bug
- **profileMatch.js**：raw `fetch()` 改用 `API.post()` + query params
- **api.js**：POST 无 body 时移除 Content-Type 头
- **modal.js**：`onConfirm` 改为 `await`，修复异步提交时 Modal 提前关闭
- **academic.js**：`user.id` 缺失时防御
- **notifications.js**：单条已读补上成功 Toast
- **parseFile.js**：上传成功补上成功 Toast

### 修改的核心文件
- `sidebar.js`、`app.js`、`router.js`、`index.html`：注册新路由和菜单项

---

## 2. 登录页面不显示

**问题**：访问首页看不到登录表单。

**原因**：`router.js` 导航到 `/login` 时，sidebar 和 topbar 仍然占据空间，登录表单被挤到一边。

**解决**：`router.js` 的 `navigate()` 中，当 `path === '/login'` 时设置 `sidebar.style.display = 'none'`、`topbar.style.display = 'none'`、`mainArea.style.marginLeft = '0'`。

---

## 3. AI 聊天窗口 — 三 Agent 分散 + "你好"误分类

**问题1**：ChatWidget 根据用户角色直接调 `/api/enterprise/chat`、`/api/student/chat`、`/api/customer/chat`，而不是用现有的统一入口 `/api/chat`。

**解决**：`chat.js` 改为统一调用 `POST /api/chat`，后端自动做顶层意图分类。

**问题2**：输入"你好"，EnterpriseAgent 返回公司制度/知识库内容，而不是闲聊。

**原因链**：
1. LLM 意图分类器把"你好"误判为 `company_guide`
2. `_handle_company_guide` 在 RAG 查询前强制拼接 `"公司 入职 制度 办公 部门"` 关键词
3. 默认 fallback 是 `data_query` 而不是 `chitchat`

**解决**：
- `prompts.py`：`chitchat` 描述改为 `"日常闲聊/寒暄/打招呼（你好/嗨/谢谢等）"`
- `agent.py`：默认 fallback 从 `data_query` 改为 `chitchat`
- `agent.py`：新增短输入预检（≤3字且无业务关键词 → 直接闲聊）
- 三个 Agent 的 `_handle_chitchat` 都加上 LLM 失败时的本地兜底回复

---

## 4. LLM 连不上（DashScope 代理问题）

**问题**：`[LLM调用失败: ProxyError ... dashscope.aliyuncs.com]`

**原因**：`requests` 库在 Windows 上自动走系统代理，代理无法连接阿里云 DashScope。

**解决**：`utils/llm_client.py` 的 `requests.post()` 加上 `proxies={"http": None, "https": None}`，强制绕过代理直连。

**验证**：curl 能通但 Python requests 不通 → 加参数后 LLM 正常返回（状态200）。

---

## 5. "查询所有员工日报" 返回 DELETE 错误

**问题**：输入"我要查询所有员工日报"，AI 输出 `SQL包含不允许的操作: DELETE`。

**原因链**：
1. LLM 正确生成 `SELECT * FROM employee_daily_report WHERE delete_flag = 0`
2. `nl2sql.py` 的 `_validate_select()` 用子串匹配检查危险关键词
3. `"DELETE" in "DELETE_FLAG"` → True → 误杀

**解决**：`nl2sql.py` 将 `DANGEROUS_KEYWORDS` 拆分为：
- `DANGEROUS_WORDS`（单字关键词）：用 `\bDELETE\b` 词边界正则匹配
- `DANGEROUS_PATTERNS`（多词/函数模式）：保留子串匹配

---

## 6. NL2SQL 页面只显示 SQL 不显示结果

**问题**：NL2SQL 查询输出 SQL 语句，没有表格结果。

**原因**：后端返回字段是 `data.data`（查询结果数组），前端读取的是 `data.results`，字段名不匹配。

**解决**：`nl2sql.js` 改为 `const rows = data.data || data.results`，兼容两种格式。

---

## 7. 文件解析功能报错（依赖缺失）

**问题**：上传 PDF 报错 `PyMuPDF和pdfplumber均未安装`。

**原因**：pip 安装到了系统 Python（Anaconda），但项目用的是 `.venv`。

**解决**：用 `.venv/Scripts/pip install pdfplumber openpyxl PyMuPDF` 安装到虚拟环境。

---

## 8. 文件解析只提取到年龄和电话

**问题**：PDF/Excel 解析后只提取了2个字段。

**原因**：`file_parser.py` 的 `_PROFILE_PATTERNS` 只有5个字段，且正则 `\S+` 只抓一个词。

**解决**：扩展到14个字段，增加性别、邮箱、微信、语言水平、家庭经济、学校、地址、备注，并改进正则为 `[^\n\r]{N,M}` 支持多词匹配。前端 `parseFile.js` 同步新增展示字段。

---

## 9. AI 输出格式可读性差

**问题**：所有 Agent 输出纯文本，换行、列表、SQL 混在一起难以阅读。

**解决**：`chat.js` 的 `formatReply()` 重写为 `markdownToHtml()`：

| 格式 | 渲染 |
|---|---|
| `**粗体**` | `<strong>` |
| `` `code` `` | 行内等宽代码 |
| ` ``` ``` ` | 深色代码块 |
| `- item` / `1. item` | 列表 |
| `## 标题` | 标题 |
| SQL 行 | 蓝色左边框高亮 |

同步在 `app.css` 添加 `.chat-code`、`.chat-list`、`.chat-sql-line` 等样式。

---

## 10. 组织架构页面混乱

**问题**：原组织架构页用嵌套 `<ul>` 树展示，信息堆在一起，层次不清晰。

**解决**：`orgChart.js` 完全重写：
- 顶部：公司蓝色渐变卡片（名称、简介、电话、邮箱）
- 中部：5个部门卡片网格（市场部📢/销售部💼/教务部📋/留学服务部🎓/客服部🎧）
- 底部：点击部门 → 显示下属小组 tags + 成员头像卡片列表

同步添加 `.org-company`、`.org-dept-grid`、`.org-member-card` 等 CSS。

---

## 11. 客服画像研判——年龄始终不匹配

**问题**：无论输入什么年龄，画像研判都不匹配任何项目。

**根因**：前端把年龄拼到 URL query string 上但 body 传 `null`，`API.post` 遇到 null body 时删除 Content-Type 头，导致 POST 请求参数解析不可靠。

**修复**：
- 后端新增 `ProfileMatchRequest` Pydantic 模型，同时兼容 JSON body 和 query 参数
- 前端改为发送标准 JSON body：`{ age: 20, education: "高中" }`

---

## 12. 前端聊天体验优化——历史面板 + 登录清空

**问题**：
- 用户重新登录后，聊天浮窗保留了上次登录的对话
- 同个用户的对话历史无处回顾

**修复**：
- `chat.js`：新增 `chatSessionId`（`crypto.randomUUID()`）用于匿名用户隔离 + localStorage 历史存取
- 登录时清空当前聊天区域，登出时自动保存会话到历史
- HTML：聊天浮窗新增左侧历史面板（240px），点击历史项可回看
- CSS：widget 宽度 380px→720px，响应式适配

---

## 13. 心理预警侧边栏权限

**问题**：侧边栏心理预警菜单对学生可见。

**修复**：`sidebar.js` 心理预警 `roles: ['ADMIN', 'EMPLOYEE']`

---

# 第二部分：后端

## 14. 投诉意图识别错误——进入了知识检索而非售后反馈

**问题**：用户输入投诉，AI 将意图错误识别为"知识检索"（FAQ），输出了公司简介"广东省教育服务有限公司（简称"粤教服务"）""，而非进入"售后反馈"分支。

**根因**：
- `STUDENT_KW` 缺少"投诉""反馈"关键词
- `CustomerServiceAgent` 没有 `feedback` 意图，投诉被归类为 `faq` → 触发 RAG 知识检索 → 输出公司信息

**修复**：
- `chat_routes.py`：`STUDENT_KW` 增加 `'投诉', '反馈', '建议', '不满', '售后'`
- `customer_service/prompts.py`：新增 `"feedback": "投诉/建议/对服务不满/反馈问题"`
- `customer_service/agent.py`：新增 `_handle_feedback` 方法，提取投诉信息并写入 `student_feedback_ticket`
- `student/agent.py`：`_handle_feedback` 改为实际写入数据库，而非只告知 API 地址

---

## 15. 用户连续发两条消息→建立了两个工单（应只建一个）

**问题**：用户输入"我要投诉"和"我的同桌王又斌扰乱课堂秩序"，AI 建立了两条投诉工单。正确行为应是：AI 判断表中必填字段，不够就追问，收齐后再写入。

**根因**：每次消息都独立触发完整意图→处理器→写入流程，没有多轮对话状态管理。

**修复——通用槽位填充框架**：
- 新建 `utils/conversation_state.py`：`SlotState`（追踪已收集/缺失字段）+ `ConversationStateManager`（基于用户 ID 管理状态）+ `TABLE_REQUIRED_FIELDS`（各表必填字段定义）
- `chat_routes.py`：步骤 0 新增状态检查——有活跃槽位状态则跳过意图识别，直接交给对应 Agent 继续收集
- `student/agent.py`：`_handle_feedback` 改为先检查 `content` 是否充分（≥8字或包含强投诉信号词），不够则追问
- 三个 Agent 均新增 `continue_data_collection` 方法处理多轮收集

**流程**：
```
用户"我要投诉" → AI："请描述具体内容"（state: collecting）
用户"同桌扰乱课堂" → AI：提取 content → 完整 → "确认提交？"（state: confirming）
用户"确认" → 写入 1 条工单
```

---

## 16. 请假日期解析失败——"明天""后天"报错

**问题**：学生输入"生病了 明天到后天"，AI 返回 `time data '明天' does not match format '%Y-%m-%d %H:%M'`。

**根因**：LLM 提取的"明天""后天"是相对表达，未被转换为绝对日期就直接传给 Pydantic 校验。

**修复——三级防御**：
- 新建 `utils/date_parser.py`：`normalize_datetime()` 将"明天/后天/下周一"等转为标准 `datetime`
- `approval_flow.py`：`extract_leave_info` 源头解析
- `student/agent.py`：`_merge_collected` 槽位合并时解析，`_commit_collected` 提交前兜底

---

## 17. 确认阶段死循环——任何输入都被当成投诉补充

**问题**：进入确认阶段（`confirming`）后，只有"确认"/"取消"能退出。用户输入"查成绩""天气"都被当成投诉补充信息，永远跳不出循环。

**根因**：
- `has_content` 阈值过低（>3字即判为有效投诉内容），"你好啊"都能触发投诉流程
- confirming 阶段没有退出机制——非确认/取消的输入全部当成补充信息循环

**修复**：
- `student/agent.py`：新增 `_has_real_feedback_content()` —— 三重判断（LLM提取"详细描述"≥8字 / 包含投诉强信号词 / ≥15字+负面词），不满足则走闲聊兜底
- `SlotState` 新增 `confirm_retries`、`SWITCH_TOPIC_KW`（切换话题关键词）
- confirming 阶段新增三条退出路径：短输入累计2次→自动取消、含切换话题词→取消、正常长文→当成补充

---

## 18. 人员权限体系重构

**问题**：
- 学生能查看心理预警（应仅员工可查）
- 员工能通过统一聊天入口请假/投诉（应仅学生可操作）
- 学生能处理投诉工单（应仅员工可操作）
- 学生能查其他学生的信息/成绩/请假/反馈（应仅查自己）
- 未登录游客应只能访问客服 Agent

**修复**：

`utils/auth.py` 新增：
- `get_optional_user`：可选登录依赖（有 token 则解析，无则返回 None）
- `enforce_self_only`：学生只能操作自己的数据，否则 403

`api/chat_routes.py`：统一聊天入口加入角色门
| LLM分类 | 游客 | STUDENT | EMPLOYEE |
|---------|------|---------|----------|
| student | →客服 | →学生 | →客服 |
| enterprise | →客服 | →客服 | →企业 |
| customer | →客服 | →客服 | →客服 |

`api/student_routes.py`：13 个端点逐个修正
- `enforce_self_only`：info/leave/feedback/academic/study-abroad/notification 查询
- `require_employee_or_admin`：feedback resolve、psych-alert 查询

前端：
- `sidebar.js`：心理预警→ADMIN/EMPLOYEE
- `feedback.js`：学生隐藏"+提交反馈"和"解决"按钮
- `router.js`：新增 `roles` 路由守卫

---

## 19. 查询请假状态→提供学生ID→被当成闲聊

**问题**：
```
学生"查询我的请假信息" → AI："请提供学生ID"
学生"7" → AI：闲聊回复（把"7"当成闲聊）
```

**根因**：查询分支只返回静态消息，没有启动会话状态追踪。后续的"7"被顶级路由当成闲聊。

**修复**：
- `_handle_admin_service` 查询分支：有 student_id+db→直接查询返回；无 student_id→启动 `admin_query` 状态
- `continue_data_collection`：新增"admin_query"意图处理——正则提取纯数字→查询 DB→返回结果

---

## 20. 学生 NL2SQL 自查询

**问题**：NL2SQL 仅员工/管理员可用，学生无法查询自己的数据。

**修复**：
- `nl2sql.py`：`NL2SQL.query()` 新增 `student_scope` 参数，自动注入 `WHERE student_id={id}`
- `student_routes.py`：新增 `POST /api/student/nl2sql`（`require_student`）
- 前端 `nl2sql.js`：学生模式——隐藏"数据更新"标签、调用学生端点、提示"仅限本人数据"
- `sidebar.js`：NL2SQL→`roles: ['ADMIN', 'EMPLOYEE', 'STUDENT']`

---

# 第三部分：架构总结

## 意图识别：两级 LLM + 本地关键词兜底 + 会话状态优先

```
POST /api/chat
  ├─ 步骤0：有活跃会话状态？→ 跳过意图识别，交给 continue_data_collection
  ├─ 步骤1：LLM 分类 TOP_LEVEL_INTENTS → 选 Agent（student/enterprise/customer）
  ├─ 步骤2：LLM 不可用 → 本地关键词打分兜底
  ├─ 步骤3：角色限制（游客→仅客服，学生→客服+学生，员工→客服+企业）
  └─ Agent 内部：LLM 分类具体意图 → 路由到处理器
```

## 槽位填充：多轮对话收集必填字段

```
用户表达插入意图
  → 提取已有字段 → 缺字段则追问（collecting 阶段）
  → 字段收齐 → 展示摘要让用户确认（confirming 阶段）
  → 用户说"确认" → 写入数据库
  → 用户说"取消" → 清除状态
  → 短输入/切换话题词 → 主动提供退出选项
```

## 日期解析：LLM 提取 + 本地解析

LLM 从自然语言中提取字段（"明天"、"后天"），本地 `normalize_datetime()` 拿 `datetime.now()` 做基准转为绝对时间。LLM 不知道"当前时间"，本地解析是准确的。

## 权限模型

| 操作 | 游客 | STUDENT | EMPLOYEE/ADMIN |
|------|------|---------|----------------|
| 统一聊天→客服Agent | ✅ | ✅ | ✅ |
| 统一聊天→学生Agent | ❌ | ✅ | ❌ |
| 统一聊天→企业Agent | ❌ | ❌ | ✅ |
| 查自己的信息/请假/反馈/教务/进度 | ❌ | ✅ | ✅ |
| 查他人的信息/请假/反馈/教务/进度 | ❌ | ❌ | ✅ |
| 提交请假/投诉 | ❌ | ✅ | ❌ |
| 处理投诉工单 | ❌ | ❌ | ✅ |
| 查心理预警 | ❌ | ❌ | ✅ |
| NL2SQL | ❌ | ✅(仅自己) | ✅(全部) |
| CRM/日报/审批 | ❌ | ❌ | ✅ |





---

# 涉及文件汇总

## 前端
| 文件 | 改动类型 |
|---|---|
| `static/js/pages/psychAlerts.js` | 新建 |
| `static/js/pages/reportsCenter.js` | 新建 |
| `static/js/pages/studentInfo.js` | 新建 |
| `static/js/pages/nl2sql.js` | 新建 + 学生模式 |
| `static/js/pages/orgChart.js` | 重写 |
| `static/js/pages/events.js` | 增强 |
| `static/js/pages/reports.js` | 增强 |
| `static/js/pages/parseFile.js` | 增强 |
| `static/js/pages/profileMatch.js` | 修复 ×2 |
| `static/js/pages/feedback.js` | 角色隐藏按钮 |
| `static/js/pages/academic.js` | 修复 |
| `static/js/pages/notifications.js` | 修复 |
| `static/js/pages/login.js` | 修改 |
| `static/js/components/chat.js` | 重写（markdown + 会话历史 + 统一端点 + sessionId） |
| `static/js/components/modal.js` | await onConfirm |
| `static/js/components/sidebar.js` | 权限修正 ×2 |
| `static/js/api.js` | null body 处理 |
| `static/js/app.js` | 路由注册 + 角色守卫 |
| `static/js/router.js` | 登录页隐藏 + 角色守卫 |
| `static/css/app.css` | Chat 历史面板 + 多组件样式 |
| `templates/index.html` | Chat 历史面板 HTML |

## 后端
| 文件 | 改动类型 |
|---|---|
| `api/chat_routes.py` | LLM优先 + 角色门 + 会话状态 + session_id |
| `api/student_routes.py` | 13端点权限修正 + 学生NL2SQL |
| `api/customer_routes.py` | ProfileMatch JSON body |
| `utils/auth.py` | `get_optional_user` + `enforce_self_only` |
| `utils/conversation_state.py` | 新建——槽位填充框架 |
| `utils/date_parser.py` | 新建——中文日期解析 |
| `agents/student/agent.py` | slot-filling + 查询会话 + 死循环修复 |
| `agents/enterprise/agent.py` | slot-filling + 短输入预检 + fallback修复 |
| `agents/enterprise/nl2sql.py` | 词边界校验 + student_scope |
| `agents/enterprise/prompts.py` | 改进意图描述 |
| `agents/customer_service/agent.py` | 新增 feedback 意图 + slot-filling |
| `agents/customer_service/prompts.py` | 新增 feedback 意图描述 |
| `agents/student/approval_flow.py` | 日期解析集成 |
| `utils/llm_client.py` | 绕过代理 |
| `utils/file_parser.py` | 14字段提取 |

---

# 第四部分：2026-05-17 会话修复记录

## 21. NL2SQL 侧边栏移除 + 整合至 AI 对话浮窗

**问题**：侧边栏出现 NL2SQL 板块，功能与 AI 对话浮窗割裂；学生无法在对话中查自己的数据。

**修复**：

- 前端：`sidebar.js` 移除 NL2SQL 菜单项；`app.js` 移除 `/nl2sql` 路由；`router.js` 移除标题映射；`index.html` 移除脚本引用
- `nl2sql.py`：`NL2SQL.__init__` 新增 `table_allowlist`、`prompt_template`、`update_whitelist` 参数，支持按角色定制实例
- `student/prompts.py`：新增 `NL2SQL_STUDENT_PROMPT`（仅5张学生表，禁止 UPDATE）和 `data_query` 意图
- `student/agent.py`：新增 `_handle_data_query()`，用受限 NL2SQL + `student_scope` 自动注入 `WHERE student_id = 当前用户ID`
- `chat_routes.py`：`STUDENT_KW` 增加查询关键词，`TOP_LEVEL_INTENTS` 更新学生描述

**权限控制**：
| 角色 | NL2SQL 范围 | UPDATE |
|------|------------|--------|
| ADMIN/EMPLOYEE | 全部表（chat → enterprise → data_query） | 白名单列 |
| STUDENT | 仅5张学生表 + student_scope | 禁止 |

---

## 22. 客户画像研判 — AI 对话中自动录入意向客户

**问题**：员工在对话框输入非结构化客户信息（如"姓名 张三 年龄 19岁 高中 想去新加坡 家里有钱"），无法自动研判和录入。

**修复**：

- `enterprise/prompts.py`：新增 `lead_profile` 意图 + `LEAD_PROFILE_PROMPT`（提取姓名/年龄/学历/意向国家/家庭经济等10个字段）
- `enterprise/agent.py`：新增三个方法：
  - `_handle_lead_profile()`：编排提取→研判→录入全流程
  - `_extract_profile()`：LLM 提取结构化信息，JSON 解析失败时用 `extract_info` 兜底
  - `_evaluate_profile()`：按画像研判规则打分（新加坡计划年龄14-19/学历/家庭经济，德国计划年龄18-35/学历/语言/动手能力），≥20分自动录入 `crm_lead`（状态"新增意向"，渠道"AI对话-画像研判"）
- `chat_routes.py`：`ENTERPRISE_KW` 增加画像研判关键词

---

## 23. 管理员对话被错误路由到客服 Agent

**问题**：管理员输入"请假"→ AI 输出"登录APS官网注册…"；输入"查询所有学生成绩"→ AI 输出"高考分数超一本线…"。两条都应该走企业 Agent。

**根因**：`chat_routes.py:137` 角色门检查失败后统一转 `customer`。LLM 把"请假""查询所有学生成绩"分类为 `student` 意图 → `_agent_allowed_for_role("student", "ADMIN")=False` → 强转 `customer` → 客服 Agent 无对应处理器 → LLM 自由发挥生成无关内容。

**修复**（三层防御）：

1. **角色门回退修正**（`chat_routes.py:137-142`）：ADMIN/EMPLOYEE 被拒后转 `enterprise` 而非 `customer`
2. **学生操作拦截器**（`enterprise/agent.py:_block_student_action()`）：在 LLM 分类前检测学生专属操作（"请假""我要投诉""我的成绩"等），有企业允许词（"审批""查询"等）则放行，否则拦截并礼貌引导
3. **LLM 意图描述优化**（`chat_routes.py:30`）：student 描述改为"留学生**个人**服务：**个人**请假申请/**本人**学业查询"

---

## 24. "查询请假记录"意图识别歧义 → 输出日报或审批指引

**问题**：管理员连续输入三次——
1. "查询请假记录" → AI 输出"共7条**日报**"（实际查到了请假数据但用日报字段格式化导致显示为空）
2. "审批学生请假" → 输出审批指引（正确）
3. "查询请假记录" → 再次输出审批指引（错误）

**根因**：EnterpriseAgent 的 LLM 意图分类存在三方歧义：
```
"report_query": "查询日报/周报数据"          ← "查询" 匹配
"data_query":   "查询数据库（成绩/进度/教务等）" ← "查询" 匹配但例子里没"请假"
"approval":     "审批请假/投诉工单"           ← "请假" 强匹配
```
LLM 无状态独立分类，两条相同输入分别命中 `report_query` 和 `approval`。`_handle_report_query` 硬编码取 `report_date`/`content` 字段导致请假数据显示为 `[]`。

**修复**（两层防御）：

1. **合并 report_query 到 data_query**（`prompts.py` + `agent.py`）：删除冗余的 `report_query` 意图，两个 handler 都调 `nl2sql.query()` 功能重复；`data_query` 示例扩展为"学生成绩/请假记录/教务DDL/客户信息/员工日报/留学进度等"；`approval` 描述加"注意：查询请假/投诉记录不是审批，属于数据查询"
2. **关键词快速路由**（`enterprise/agent.py:_quick_route()`）：在 LLM 分类前按关键词直接路由——含"查询"/"记录"/"列表"等 → `data_query`；含"审批"/"通过"/"驳回"+"请假"/"投诉" → `approval`；含"提交"/"录入"/"新增"等非查询词 → 跳过快速路由交 LLM 处理

---

## 25. AI 对话中完成请假审批

**问题**：老师/管理员无法在 AI 对话中直接审批学生请假，`_handle_approval` 只返回 API 端点指引。

**修复**（`enterprise/agent.py:_handle_approval` 完全重写）：

- LLM 提取：审批决定（通过/驳回）、学生姓名、申请编号、审批意见
- **按编号审批**：查 `StudentAdminService` → 校验状态 → 执行审批 → 创建通知给学生
- **按姓名审批**：查 `SysUser` → 找待审批请假 → 单条自动批、多条列出供选择
- **无目标时**：列出全部待审批请假，引导用户指定
- `chat_routes.py` 向 `route_intent` 传递 `user_id`，用于记录审批人
- 已审批的申请不可重复审批（状态校验）

**审批示例**：
| 输入 | 行为 |
|------|------|
| "通过请假申请 #3" | 按编号审批 → 通知学生 |
| "通过张三的请假" | 按姓名查→单条自动批 |
| "驳回李四的请假，原因：理由不充分" | 驳回+记录原因 |
| "查看待审批请假" | 列出全部待审批 |

---

# 涉及文件汇总（本次会话新增/修改）

## 前端
| 文件 | 改动类型 |
|---|---|
| `static/js/components/sidebar.js` | 移除 NL2SQL 菜单项 |
| `static/js/app.js` | 移除 NL2SQL 路由注册 |
| `static/js/router.js` | 移除 NL2SQL 标题映射 |
| `templates/index.html` | 移除 nl2sql.js 脚本引用 |

## 后端
| 文件 | 改动类型 |
|---|---|
| `agents/enterprise/nl2sql.py` | 可配置 table_allowlist / prompt_template / update_whitelist |
| `agents/enterprise/prompts.py` | 新增 lead_profile 意图 + LEAD_PROFILE_PROMPT；删除 report_query；精确化 data_query/approval 描述 |
| `agents/enterprise/agent.py` | 新增 _handle_lead_profile / _extract_profile / _evaluate_profile / _block_student_action / _quick_route；重写 _handle_approval；删除 _handle_report_query；route_intent 新增 user_id 参数 |
| `agents/student/prompts.py` | 新增 NL2SQL_STUDENT_PROMPT + data_query 意图 |
| `agents/student/agent.py` | 新增 _handle_data_query（受限 NL2SQL + student_scope） |
| `api/chat_routes.py` | 角色门回退修正 + TOP_LEVEL_INTENTS 优化 + ENTERPRISE_KW/STUDENT_KW 扩展 + 传递 user_id |
| `tests/test_frontend.py` | NL2SQL 页面测试改为对话浮窗测试 |


---

# 第五部分：2026-05-17 功能开发 — 7 项需求实现

## 26. 学生反馈后管理员收不到通知

**问题**：学生提交反馈（`POST /api/student/feedback`）后只创建工单，管理员和班主任的通知中心无任何提示，只能手动去反馈工单列表查看。

**根因**：`create_feedback` 只调了 `FeedbackCRUD.create`，没有创建 Notification。通知仅在反馈**被处理**时才创建（`resolve_feedback` → `feedback_resolved`）。

**修复**（`api/student_routes.py`）：

- 创建反馈后查询所有 `ADMIN` 用户 + 该学生的 `head_teacher_id`
- 为每个管理员/班主任发送 `new_feedback` 通知（标题"新反馈工单"，含学生姓名、反馈类型、内容摘要、紧急程度）
- 同时给提交反馈的学生发确认通知（`feedback_submitted`）

**关键改动**：

```python
# 给管理员和班主任发送通知
recipients = set()
admins = db.query(SysUser).filter(SysUser.user_type == "ADMIN", SysUser.delete_flag == 0).all()
for admin in admins:
    recipients.add(admin.id)
if student.head_teacher_id:
    recipients.add(student.head_teacher_id)

for recipient_id in recipients:
    NotificationCRUD.create(db, recipient_id=recipient_id, title="新反馈工单",
        content=f"学生 {student.real_name} 提交了{req.feedback_type}...",
        notification_type="new_feedback", related_id=ticket.id)
```

---

## 27. 管理员无法修改留学进度 + 员工通讯录

**问题**：
- 留学进度只有 GET 查询接口，管理员无法在系统中修改学生的留学阶段状态
- 员工通讯录只有 GET 查询接口，无法更新员工联系方式/部门/角色

**修复（后端）**：

| 新增端点 | 方法 | 说明 |
|---------|------|------|
| `/api/student/study-abroad/{id}` | PUT | 修改留学进度（仅 EMPLOYEE/ADMIN） |
| `/api/enterprise/employee/{id}` | PUT | 修改员工信息（仅 EMPLOYEE/ADMIN） |

**CRUD 层新增**：
- `StudyAbroadCRUD.update()`：更新留学进度，设 `is_current=1` 时自动清除同学生其他记录的 `is_current`
- `EmployeeCRUD.update()`：更新员工非 None 字段

**前端**：
- `studyAbroad.js`：每个阶段卡片增加"✏️ 编辑"按钮，模态框编辑阶段/状态/负责人/日期
- `employees.js`：每行增加"✏️ 编辑"按钮，模态框编辑姓名/角色/部门/电话/邮箱

---

## 28. 课程项目无添加/删除功能

**问题**：课程项目页面只能查看，没有添加和删除入口。

**修复（后端）**：

| 新增端点 | 方法 | 权限 | 说明 |
|---------|------|------|------|
| `/api/enterprise/project` | POST | EMPLOYEE/ADMIN | 添加课程项目 |
| `/api/enterprise/project/{id}` | DELETE | 仅 ADMIN | 软删除（`delete_flag=1`） |

**CRUD 层新增**：`ProjectCRUD.delete()`

**前端**（`projects.js`）：
- 页头增加"+ 添加项目"按钮（EMPLOYEE/ADMIN 可见），弹出表单模态框
- 每个项目卡片右上角增加"🗑️ 删除"按钮（仅 ADMIN 可见），二次确认后删除

---

## 29. 文件解析 → 客户意向研判 + 自动录入 CRM

**问题**：原来的文件解析只提取画像字段（姓名/年龄/学历等），不做意向研判，不录入 CRM。上传文件后还要人工判断是否为意向客户。

**修复**：

**核心函数** `assess_lead_intention()`（`utils/file_parser.py`，需求 29 & 32 共用）：

- 根据 `knowledge_base/data/用户研判规则/用户画像研判规则.md` 实现双项目评分：
  - **新加坡国际本硕升学计划**：年龄 14-19、初中/高中/中职学历、家庭经济
  - **中德精英人才共建计划**：年龄 18-35、高中及以上学历、语言能力、家庭经济
- 评分维度：年龄匹配（25-30分）、学历匹配（20-25分）、意向国家（15分）、家庭经济（10分）、语言能力（5-15分）、留学意愿（15分）
- 总分 ≥50 → 判定为意向客户，返回 `lead_data` 供写入 CRM
- 总分 <50 → 非意向客户，返回原因分析

**文件解析端点改造**（`POST /api/customer/parse-file`）：
```
上传文件 → 解析文本 → 提取画像 → assess_lead_intention() → 意向客户? → 自动写入 crm_lead
```

**前端**（`parseFile.js`）：展示研判结果卡片（绿色=意向客户 / 红色=非意向），显示评分、匹配项目、研判依据、是否已录入 CRM

---

## 30. 学生成绩批量上传

**问题**：成绩只能逐条录入，无法批量导入。

**修复（后端）**：

| 新增端点 | 方法 | 说明 |
|---------|------|------|
| `/api/enterprise/score/batch` | POST | 上传 Excel/CSV，批量导入成绩 |

**新增函数**：
- `parse_score_file()`（`utils/file_parser.py`）：解析 Excel/CSV → 结构化成绩列表，支持中英文列名映射，校验必填字段
- `ScoreCRUD.batch_create()`（`crud/enterprise_crud.py`）：逐条校验学生存在性 → 检查重复（相同学期+课程+考试类型）→ 批量插入 → 返回成功/失败统计

**前端**（`scores.js`）：页头增加"📤 批量导入"按钮，上传后弹窗展示成功/失败统计和失败行详情

---

## 31. 员工离职处理（暂缓）

**决定**：此需求暂时不实现，后续再议。

规划中的方案（待后续启用）：
- `PUT /api/enterprise/employee/{id}/resign` — 设置 `status="离职"` + `delete_flag=1`
- CRM 客户交接：名下 `crm_lead` 的 `owner_employee_id` 重新分配
- 班主任交接：名下学生的 `head_teacher_id` 重新分配

---

## 32. AI 对话浮窗中自然语言研判意向客户

**问题**：管理员/员工在 AI 对话浮窗中用自然语言描述客户信息（如"客户名刘帅 家庭经济良好 学历本科"），需要能自动研判并录入 CRM。

**修复**：

**EnterpriseAgent 增强**：
- `_handle_lead_profile` 改为调用统一的 `assess_lead_intention()`（与需求 29 共用规则）
- `_quick_route` 新增 `lead_profile` 快速触发关键词（"画像""研判""意向客户""是不是意向""评估一下" 等）

**chat_routes.py 关键词增强**：
- `ENTERPRISE_KW` 新增 `'是不是意向', '评估一下', '分析一下', '匹配项目', '意向客户'`

**流程**：
```
用户在浮窗输入"刘帅 本科 家庭良好 是否为意向客户"
  → /api/chat → LLM 分类 enterprise → EnterpriseAgent
  → _quick_route 匹配 lead_profile → _handle_lead_profile
  → _extract_profile (LLM) 提取结构化字段
  → assess_lead_intention() 评分
  → ≥50分：标注"✅ 意向客户" → 自动写入 crm_lead → 返回结果
  → <50分：标注"❌ 暂不符合" → 展示原因 → 不写入
```

---

# 第六部分：Bug 修复 — 对话研判未写入 CRM + 缺年龄评分过低

## 33. 对话研判识别为意向客户但未写入 crm_lead

**问题**：员工输入"客户名刘帅 家庭经济情况良好 学历本科 留学意念强烈 是否为公司的意向用户"，AI 正确回答"该用户为意向用户"，但 `crm_lead` 表中没有该客户记录。

**根因（两个）**：

**Bug 1 — 事务未提交**：[agent.py:351](agents/enterprise/agent.py#L351) `_handle_lead_profile` 中 CRM 写入用的是 `db.flush()`（只将会话刷到数据库连接但不提交事务）。`/api/chat` 路由调用 Agent 后也没有 `db.commit()`。请求结束事务回滚，数据丢失。

**Bug 2 — 缺年龄时评分过低**：用户没提供年龄（如只说"学历本科"），`assess_lead_intention()` 中年龄是核心评分项——新加坡项目需 14-19 岁（30分）、德国项目需 18-35 岁（25分）。缺年龄时全部年龄分丢失，其他维度（学历20+经济10）总分最高30-35，远不到50分阈值。函数返回 `is_intended: False`，不写 CRM。

**修复**：

**Bug 1**：`db.flush()` → `db.commit()`

**Bug 2**：`assess_lead_intention()` 新增学历推断年龄逻辑：
- **大专/本科/硕士/博士** → 推断 ≥18 岁（德国项目范围）→ +15 分年龄推断分 + `de_age_match=True`
- **高中/职高/中专/中技** → 推断 16-19 岁（新加坡项目范围）→ +15 分年龄推断分 + `sg_age_match=True`

修复后的评分（刘帅案例：本科 + 良好经济，缺年龄）：
| 维度 | 得分 |
|------|------|
| 学历匹配德国项目（本科 ≥ 高中） | +20 |
| 学历推断年龄范围（本科 → 18+） | +15 |
| 家庭经济支持（良好） | +10 |
| 基本条件满足德国项目意愿加分 | +15 |
| **总分** | **60 ≥ 50 ✅** |

修复后正确判定为意向客户并写入 `crm_lead`。

---

# 涉及文件汇总（本次会话新增/修改）

## 后端
| 文件 | 改动类型 |
|---|---|
| `api/student_routes.py` | 反馈通知 + 留学进度 PUT 端点 |
| `api/enterprise_routes.py` | 员工 PUT + 项目 POST/DELETE + 成绩批量 POST |
| `api/customer_routes.py` | 文件解析改造：研判 + 自动录入 CRM |
| `api/chat_routes.py` | ENTERPRISE_KW 关键词增强 |
| `crud/student_crud.py` | StudyAbroadCRUD.update()（含 is_current 互斥） |
| `crud/enterprise_crud.py` | EmployeeCRUD.update() + ScoreCRUD.batch_create() |
| `crud/customer_crud.py` | ProjectCRUD.delete() |
| `schemas/schemas.py` | StudyAbroadUpdateRequest / EmployeeUpdateRequest / ProjectCreateRequest / ScoreBatchItem |
| `schemas/__init__.py` | 导出新 Schema |
| `utils/file_parser.py` | assess_lead_intention()（统一研判）+ parse_score_file() + 学历推断年龄 |
| `agents/enterprise/agent.py` | _handle_lead_profile 改用统一研判 + db.flush→commit + _quick_route 增 lead_profile 关键词 |

## 前端
| 文件 | 改动类型 |
|---|---|
| `static/js/pages/studyAbroad.js` | 新增编辑按钮 + 模态框 |
| `static/js/pages/employees.js` | 新增编辑按钮 + 模态框 |
| `static/js/pages/projects.js` | 新增添加/删除按钮 + 模态框 |
| `static/js/pages/parseFile.js` | 新增研判结果卡片展示 |
| `static/js/pages/scores.js` | 新增批量导入按钮 |

---

# 第七部分：2026-05-17 — 槽位填充死循环 + NL2SQL 占位符 + 错误信息泄露

## 34. 槽位填充死循环——用户一旦进入投诉流程就逃不出来

**问题**：学生提问"查个人信息"→ AI 返回 NL2SQL 错误 → 学生测试提交投诉 → 之后无论输入什么（查成绩、查进度等），AI 始终回复"好的，已更新信息。请确认以下内容：• 学生ID: 7 • 投诉/反馈内容: 查询投诉进度"，永远跳不出投诉确认循环。

**根因（4 个叠加）**：

1. **触发门槛过低**：`_handle_feedback` 的 `STRONG_COMPLAINT_KW` 包含 `"投诉"`，用户输入"查询投诉进度"被判定为"真投诉内容"，整句话当成投诉内容存入，直接进入 `confirming` 阶段。

2. **"收集阶段"无话题切换检测**：`continue_data_collection` 的"收集阶段"(collecting) 没有 `SWITCH_TOPIC_KW` 检查，所有用户输入都被当成槽位数据吸收。

3. **`SWITCH_TOPIC_KW` 覆盖不足**：只有 14 个关键词，常见查询如"我的分数是多少""帮我看看我的信息""最近有什么通知"等全部不匹配。

4. **确认阶段条件 C 死循环**：`continue_data_collection` 确认阶段中，用户输入未命中取消/确认/短输入/话题切换任何一条时走到条件 C——切到 collecting → `_merge_collected` 但 `missing=[]` 无字段可更新 → `is_complete()=True` 立即切回 confirming → 返回相同确认提示 → 用户再输入 → 重复。**无限循环**。

**修复——4 层逃生机制**：

| 层 | 机制 | 触发条件 | 延迟 |
|---|---|---|---|
| 1 | 关键词匹配（34 词） | 收集/确认阶段命中 SWITCH_TOPIC_KW | 0 |
| 2 | LLM 意图复核 | `chat_routes.py` 有活跃状态时先用 LLM 判断"补充信息"还是"新话题" | ~500ms |
| 3 | 交互计数兜底 | `SlotState.interaction_count` 超过 5 轮未确认自动清状态 | 到第 6 轮触发 |
| 4 | 查询/投诉区分 | `_handle_feedback` 检测到"查询投诉进度"等查询关键词→查 DB 返工单列表，不建新工单 | 0 |

**修改文件**：
| 文件 | 改动 |
|---|---|
| `utils/conversation_state.py` | `SWITCH_TOPIC_KW` 14→34 词；`SlotState` 新增 `interaction_count` + `MAX_INTERACTIONS=5`；`ConversationStateManager` 新增 `_sweep_expired()` 防内存泄漏 |
| `api/chat_routes.py` | 新增 `TOPIC_SWITCH_CHECK_PROMPT` + `_llm_check_topic_switch()`，活跃状态时先 LLM 复核再决定继续填充还是清状态重路由 |
| `agents/student/agent.py` | `continue_data_collection`：收集阶段新增话题切换检测 + 交互计数兜底；确认阶段条件 C 拆分——`is_complete()` 直接清状态不循环；`_handle_feedback` 新增查询投诉关键词→直接查 DB 返回工单 |
| `agents/customer_service/agent.py` | `continue_data_collection` 同步上述 4 层；`_handle_feedback` 同步查询投诉检测 |
| `agents/enterprise/agent.py` | `continue_data_collection` 同步交互计数 + 收集阶段话题切换 + 条件 C 拆分 |

---

## 35. "查看我的请假记录"→ SQL 占位符 `?` 语法错误

**问题**：学生输入"查看我的请假记录"，AI 返回：
```
SQL执行失败: (pymysql.err.ProgrammingError) ... near '? AND delete_flag = 0 ...'
[SQL: SELECT ... FROM student_admin_service WHERE student_id = ? AND delete_flag = 0 ...]
```

**根因**：[nl2sql.py:212](agents/enterprise/nl2sql.py#L212) 的 `_apply_student_scope` 方法一行代码：

```python
has_student_table = any(t in upper for t in student_tables)
```

`student_tables` 表名全是**小写**（`"student_admin_service"`），`upper = sql.upper()` 把 SQL 全转**大写**（`"STUDENT_ADMIN_SERVICE"`），Python `in` 区分大小写，`has_student_table` 始终为 `False`，整个 student_id 注入逻辑被跳过。LLM 生成的 `?` 占位符原封不动到 MySQL，`?` 在 MySQL 中不是合法占位符（应用 `%s`），SQL 执行报错。

**修复**：一行改动 — `t in upper` → `t.upper() in upper`

**修改文件**：`agents/enterprise/nl2sql.py` 第 212 行

---

## 36. SQL 错误信息直接暴露给用户

**问题**：NL2SQL 查询失败时，`ProgrammingError`、`pymysql`、原始 SQL 语句全部展示给学生。既不友好也暴露数据库结构。

**根因**：错误从底层层层透传未包装：
- `nl2sql.execute()` → `f"SQL执行失败: {e}"`
- `nl2sql.query()` → `return {"error": str(e), "sql": sql}`（SQL 一并返回）
- `_handle_data_query()` → `f"查询失败: {result['error']}..."` 直接展示
- 成功路径也展示 `执行SQL: \`{sql}\`` 原始 SQL

**修复**：
- `student/agent.py` 和 `enterprise/agent.py` 所有 NL2SQL 调用处：错误走 `logging.error` 记录详情（含 SQL），用户只看到"查询失败，请尝试更具体的描述…"
- 成功路径去掉原始 SQL 展示，只返回解释和结果数据

**修改文件**：
| 文件 | 改动 |
|---|---|
| `agents/student/agent.py:_handle_data_query` | 错误→日志 + 友好提示；成功→去 SQL 展示 |
| `agents/enterprise/agent.py:_handle_lead_query` | 同上 |
| `agents/enterprise/agent.py:_handle_data_query` | 同上 |

---

# 涉及文件汇总（本次会话新增/修改）

## 后端
| 文件 | 改动类型 |
|---|---|
| `utils/conversation_state.py` | SWITCH_TOPIC_KW 扩充 + interaction_count + MAX_INTERACTIONS + _sweep_expired |
| `api/chat_routes.py` | 新增 LLM 意图复核（第二层逃生） |
| `agents/student/agent.py` | 4层逃生 + 查询投诉检测 + 错误信息脱敏 |
| `agents/customer_service/agent.py` | 4层逃生 + 查询投诉检测 |
| `agents/enterprise/agent.py` | 4层逃生 + 错误信息脱敏 |
| `agents/enterprise/nl2sql.py` | _apply_student_scope 大小写修复 |
