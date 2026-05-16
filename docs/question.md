# 前端全功能调试记录

日期：2026-05-16 ~ 2026-05-17

---

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

## 涉及文件汇总

| 文件 | 改动类型 |
|---|---|
| `static/js/pages/psychAlerts.js` | 新建 |
| `static/js/pages/reportsCenter.js` | 新建 |
| `static/js/pages/studentInfo.js` | 新建 |
| `static/js/pages/nl2sql.js` | 新建 |
| `static/js/pages/orgChart.js` | 重写 |
| `static/js/pages/events.js` | 增强 |
| `static/js/pages/reports.js` | 增强 |
| `static/js/pages/parseFile.js` | 增强 |
| `static/js/pages/profileMatch.js` | 修复 |
| `static/js/pages/academic.js` | 修复 |
| `static/js/pages/notifications.js` | 修复 |
| `static/js/pages/login.js` | 修改 |
| `static/js/components/chat.js` | 重写 formatReply + 统一端点 |
| `static/js/components/modal.js` | await onConfirm |
| `static/js/components/sidebar.js` | 新增菜单项 |
| `static/js/api.js` | null body 处理 |
| `static/js/app.js` | 注册路由 + 简化 agent |
| `static/js/router.js` | 登录页隐藏 sidebar + 新标题 |
| `static/css/app.css` | 新增多组件样式 |
| `templates/index.html` | 加载新脚本 |
| `api/chat_routes.py` | LLM优先 + 本地关键词兜底 |
| `agents/enterprise/agent.py` | 短输入预检 + fallback修复 + 本地闲聊 |
| `agents/enterprise/prompts.py` | 改进意图描述 |
| `agents/enterprise/nl2sql.py` | 词边界安全校验 |
| `agents/student/agent.py` | 本地闲聊fallback |
| `agents/customer_service/agent.py` | 本地闲聊fallback |
| `utils/llm_client.py` | 绕过代理 |
| `utils/file_parser.py` | 14字段提取 |
