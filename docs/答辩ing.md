# 粤教服务 AI Agent 答辩问题与参考答案

---

## 零、AI 范式与核心模式（1题）

### Q0：这个项目体现了哪些 AI 相关的范式（如 RAG、Agent、NL2SQL 等）？

**答：**

本项目共体现了 **8 个核心 AI 范式**，覆盖从意图理解到知识检索、从自然语言查询到多轮对话的完整链路：

---

**1. Multi-Agent 协作（多智能体）**

三个专业 Agent 分工协作：客服 Agent（访客/家长）、企业助手 Agent（员工/管理层）、学生助手 Agent（在册留学生）。顶层的 `chat_routes.py` 作为调度器，先用 LLM 做意图分类决定路由到哪个子 Agent，每个 Agent 再内部做二级意图路由到具体处理器。三个 Agent 共享 RAG 引擎、槽位填充管理器、NL2SQL 引擎和画像研判算法。

---

**2. RAG（检索增强生成）**

自研的纯 Python 检索引擎（`knowledge_base/vectorizer.py`），零外部依赖：
- **倒排索引** + **1~3 gram 分词** + **IDF 加权** + **覆盖率评分**（非向量检索，而是 BM25 风格的词汇检索）
- **同义词展开**：52 条映射（如"多少钱"→"学费/费用/价格"），解决口语到书面语的匹配问题
- **精确子串加分**：用户输入完全包含在 QA 问题中时额外加权
- 评分公式：`覆盖率×0.45 + Jaccard×0.15 + 命中数加分 + 精确匹配加分`
- 283 条 QA 对覆盖公司业务、留学政策、公司信息、新人指南四大领域

不用向量数据库的理由：业务以结构化 FAQ 为主，关键词匹配已足够精准，零依赖便于部署。

---

**3. NL2SQL（自然语言转 SQL）**

将用户自然语言转为 MySQL SELECT/UPDATE 语句，包含完整安全机制：
- **表/列白名单**：SELECT 限 11 张表，UPDATE 限 4 张表的特定列
- **强制约束**：UPDATE 必须有 WHERE + LIMIT，SELECT 必须加 `delete_flag=0`
- **危险关键词拦截**：INSERT/DELETE/DROP/ALTER/TRUNCATE/CREATE 等一律拒绝
- **学生数据隔离**：自动注入 `student_id = 当前用户ID` 到 WHERE 条件
- Prompt 中嵌入完整数据库 schema 及字段中文含义

---

**4. Prompt Engineering（提示词工程）**

系统多个模块依赖精心设计的 Prompt：
- **角色设定**：「你是粤教服务的智能客服助手小粤」「你是留学生的心理健康关怀助手」
- **输出格式约束**：「只返回 JSON，不要其他内容」——所有结构化输出都走 JSON 格式
- **Few-shot 示例**：意图分类 Prompt 中包含 3 个输入→意图映射示例
- **安全规则嵌入**：NL2SQL Prompt 包含表和列的白名单说明、危险操作禁止规则
- **评估标准嵌入**：心理监测 Prompt 中写明了高/中/低风险级别的划分标准

---

**5. Intent Classification（意图识别）**

双层意图分类机制：
- **第一层（关键词快速路由）**：输入 < 4 字时直接查关键词表，毫秒级响应
- **第二层（LLM 意图分类）**：构造包含意图列表 + 描述 + 示例的 Prompt，LLM 返回 `{intent, confidence, entities}` JSON
- 三层意图空间：顶层路由 3 类 → 各 Agent 内部 9~10 种子意图，共 28 种意图
- fallback 机制：LLM 不可用时降级为本地关键词打分分类

---

**6. Slot Filling / Dialogue State（槽位填充 / 多轮对话状态管理）**

`ConversationStateManager` 实现对话状态跟踪：
- **槽位定义**：每个意图定义必填字段（如请假需要 `leave_type, start_time, end_time, reason`）
- **多轮收集**：状态机 `collecting → confirming → done`，逐槽收集缺失字段
- **取消/确认检测**：「算了」「取消」→ 清除状态；「确认」「是的」→ 提交到数据库
- **话题切换检测**：三层逃逸机制（关键词 + LLM 判断 + 交互次数上限 5 次）
- **TTL 机制**：600 秒自动过期，防止僵尸状态

---

**7. Structured Output / LLM as Tool（LLM 作为结构化提取工具）**

`LLMClient.extract_info()` 把 LLM 当作通用的信息提取工具：
- 输入：用户自由文本 + 需要提取的字段列表
- 输出：`{field1: value1, field2: value2, ...}` JSON
- 用于画像提取（姓名/年龄/意向国家/语言水平）、请假信息提取、投诉内容结构化、日报摘要等 10+ 场景
- 本质上等价于 Function Calling / Tool Use，通过 Prompt + JSON 约束实现

---

**8. Hybrid Rule + LLM（规则 + LLM 混合决策）**

多个模块采用规则优先、LLM 兜底的混合策略：
- **心理监测**：14 个高危词 + 28 个中危词关键词毫秒级检测 → 不够用时再调 LLM 深度评估
- **画像研判**：年龄、学历、语言、经济四维评分算法（规则打分）→ 分数不足以判断时再用 LLM 分析
- **话题切换检测**：关键词优先（毫秒级）→ 不确定时调 LLM 判断
- **意图分类**：短输入关键词匹配优先 → 复杂输入调 LLM

---

**其他相关范式**（简要）：

| 范式 | 体现位置 | 说明 |
|------|---------|------|
| **Chain-of-Thought** | `nl2sql.py` / `psych_monitor.py` | temperature=0.1 + 详细 Prompt 引导逐步推理 |
| **LLM-as-Judge** | `chat_routes.py` 话题切换检测 / `agent.py` 反馈内容真实性判断 | 用 LLM 做二分类评估 |
| **Proactive AI** | `scheduler.py` 定时任务 | 自动生成周报、DDL 提醒、跟进催办 |
| **Graceful Degradation** | 所有 Agent | LLM 不可用时降级到本地规则/模板 |
| **Report Generation** | `report_generator.py` | 5 类 AI 报告（客户分析/日报/周报/心理周报/投诉周报），LLM 生成 + 本地模板兜底 |
| **Voice (ASR+TTS)** | `voice_processor.py` | Whisper 语音转文字 + TTS 文字转语音 |

---

**一句话总结**：项目以 **Multi-Agent + RAG + NL2SQL + Slot Filling** 四大范式为主干，**Prompt Engineering + Intent Classification + Structured Output** 为通用能力，**Hybrid Rule+LLM + Graceful Degradation** 为可靠性保障，形成了一个覆盖获客→管理→服务全链路的 AI Agent 系统。

---

## 一、项目概述与架构设计（5题）

### Q1：请简要介绍你这个项目的核心定位和解决的问题？

**答：**

本项目"粤教服务 AI Agent"是为**广东省教育服务有限公司**打造的智能对话服务系统，核心解决三大业务痛点：

1. **获客效率低**：传统电话/面谈获客成本高，客服Agent可7×24自动应答、推荐项目、研判意向
2. **内部管理散**：员工日报/CRM/审批等依赖手工流转，企业助手通过NL2SQL、语音日报、智能审批提升效率
3. **学生服务缺**：留学生请假/投诉/心理/教务等缺乏统一入口，学生助手提供一站式对话服务

系统采用**FastAPI + SQLAlchemy + LLM**技术栈，面向三类用户（访客/员工/学生）提供3个专业AI Agent，覆盖28种意图路由，15张数据表，6大业务模块。

---

### Q2：你采用了什么技术架构？为什么这样选型？

**答：**

采用**三层架构 + 多Agent协作**：

| 层级 | 技术 | 选型理由 |
|------|------|---------|
| 路由层 | FastAPI | 异步高性能、自动API文档、依赖注入天然适合权限控制 |
| 数据层 | SQLAlchemy + SQLite/MySQL | ORM抽象、支持多数据库切换、软删除统一 |
| AI层 | OpenAI兼容LLM + RAG | 意图分类/槽位填充/知识检索，兼容多家模型供应商 |
| 前端 | 原生JS + Hash路由 | 零依赖轻量SPA，演示部署简单 |

**关键设计决策**：
- **不选LangChain**：项目需要精细控制Prompt和槽位填充逻辑，自定义比框架更灵活
- **RAG自研而非向量库**：业务以FAQ问答为主，关键词+覆盖率检索足够，且零外部依赖便于部署
- **SQLite/MySQL双模**：开发用SQLite零配置，生产切MySQL保证并发性能

---

### Q3：三个Agent（客服/企业/学生）是如何分工的？有没有共享逻辑？

**答：**

| 维度 | 客服Agent | 企业助手Agent | 学生助手Agent |
|------|----------|-------------|-------------|
| 用户 | 访客/家长 | 员工/管理层 | 在册留学生 |
| 意图数 | 9种 | 10种 | 9种 |
| 核心 | 咨询/推荐/报名 | CRM/日报/NL2SQL | 请假/心理/教务 |
| 认证 | 无需登录 | JWT(员工/管理员) | JWT(学生) |
| 特色 | RAG+FAQ检索 | NL2SQL+语音日报 | 心理监测+审批流程 |

**共享逻辑**：
- `assess_lead_intention()` — 客服画像研判和企业助手画像研判共用同一套打分规则
- `RAGEngine` — 三者共用同一套知识库和检索引擎
- `ConversationStateManager` — 槽位填充状态管理器为所有Agent共享
- `NL2SQL` — 企业助手和学生助手都支持自然语言查询（学生限定本人数据）
- `NotificationCRUD` — 审批/反馈/请假等业务通知统一创建

---

### Q4：你的RAG检索引擎是怎么实现的？为什么不用向量数据库？

**答：**

采用**关键词+覆盖率混合检索**，而非向量数据库，原因和实现如下：

**不用向量数据库的理由**：
1. 业务以结构化FAQ为主（283条QA对），关键词匹配已足够精准
2. 避免引入Milvus/Chroma等额外部署依赖，降低运维复杂度
3. 中文语义向量模型质量参差不齐，自建成本高

**检索算法**（`vectorizer.py`）：
1. **倒排索引**：对QA对构建1-3 gram索引，过滤停用词
2. **IDF加权覆盖率**：稀有词命中权重更高，`覆盖率 = 命中词数/问题总词数`
3. **同义词展开**：52条口语→书面语映射（如"多少钱"→"学费/费用/价格"）
4. **精确子串加分**：用户输入完全包含在问题中时额外加分
5. **评分公式**：`覆盖率×0.45 + Jaccard×0.15 + 命中数加分 + 精确匹配加分`

**局限性**：对语义相似但词汇不同的问法召回较弱，后续可升级为向量检索。

---

### Q5：系统的数据模型是怎么设计的？为什么用统一用户表而不是分表？

**答：**

共15张表，核心设计是**统一用户表（SysUser）**通过`user_type`字段区分ADMIN/EMPLOYEE/STUDENT三种角色。

**用统一表而非分表的理由**：
1. **认证统一**：登录只需查一张表，JWT的`sub`统一指向`sys_user.id`
2. **权限统一**：`get_current_user`依赖注入只需一套逻辑
3. **关联简化**：学生`head_teacher_id`直接关联`sys_user.id`，无需跨表JOIN
4. **通知统一**：`notification.recipient_id`可指向任何角色用户

**角色差异化通过字段实现**：
- EMPLOYEE独有：`employee_role`（班主任/市场专员等）
- STUDENT独有：`head_teacher_id`（关联班主任）
- ADMIN：无额外字段，通过`user_type=ADMIN`标识

**所有表统一的软删除模式**：`delete_flag`字段（0=正常，1=删除），查询时过滤，保证数据可恢复。

---

## 二、AI Agent 技术细节（5题）

### Q6：你的意图分类是怎么做的？准确率如何保证？

**答：**

采用**LLM意图分类 + 关键词快速路由**双层机制：

**第一层：关键词快速路由**（企业助手）
- 短输入预检：输入<4字时直接查关键词表（如"请假"→admin_service，"客户"→lead_query）
- 避免短输入给LLM造成分类歧义

**第二层：LLM意图分类**
- 构造包含意图列表和示例的Prompt，让LLM输出结构化JSON
- 每个Agent有独立的Prompt模板，定义各自的意图空间

**准确率保障措施**：
1. **意图空间隔离**：每个Agent只路由到自己能力范围内的意图，避免跨域干扰
2. **Few-shot示例**：Prompt中包含典型输入→意图的映射示例
3. **Fallback机制**：无法分类时默认路由到`chitchat`，保证不中断
4. **学生操作拦截**（企业助手）：检测到学生相关操作时，提示用户使用学生通道

---

### Q7：槽位填充（Slot Filling）是怎么实现的？举一个具体例子说明完整流程。

**答：**

槽位填充使用`ConversationStateManager`管理多轮对话状态，以**请假申请**为例：

```
用户: "我想请假"
  ↓ Agent识别意图: admin_service
  ↓ 创建会话状态: {intent: admin_service, slots: {leave_type: null, start_time: null, end_time: null, reason: null}, stage: collecting}

Agent: "请问您要请什么假？（病假/事假）"
用户: "病假"
  ↓ 填充 slot: leave_type = "病假"

Agent: "请告诉我请假的起止时间"
用户: "明天到后天"
  ↓ date_parser解析: start_time = 2026-05-17, end_time = 2026-05-18
  ↓ 填充 slot: start_time, end_time

Agent: "请告诉我请假原因"
用户: "身体不舒服"
  ↓ 填充 slot: reason = "身体不舒服"
  ↓ 所有必填槽位已填充 → stage: confirming

Agent: "请确认：病假，2026-05-17至2026-05-18，原因：身体不舒服。确认提交吗？"
用户: "确认"
  ↓ stage: done → 调用 StudentServiceCRUD.create_leave() 写入数据库
```

**关键实现细节**：
- `ConversationStateManager`使用内存字典，TTL=600秒自动过期
- 必填字段定义在`conversation_state.py`的`REQUIRED_SLOTS`字典中
- 支持话题切换检测：检测到"算了/取消"等关键词时清除状态
- 交互次数上限（MAX_INTERACTIONS=5），超过时主动终止

---

### Q8：NL2SQL是怎么保证安全性的？万一用户输入"删除所有数据"怎么办？

**答：**

NL2SQL采用**三层安全防护**：

**第一层：SQL白名单**
- **SELECT白名单**：只允许查11张表（sys_user/crm_lead/student_score等）
- **UPDATE白名单**：只允许改4张表的特定列：
  - `crm_lead`：status/next_follow_time/score
  - `student_feedback_ticket`：status/solution
  - `student_admin_service`：status/reject_reason
  - `student_academic`：ddl_status
- 绝对禁止INSERT/DELETE/DROP/ALTER/TRUNCATE

**第二层：SQL结构校验**
- 必须包含WHERE子句（防止全表更新）
- 必须包含LIMIT（防止返回全量数据，默认上限100）
- 词边界匹配危险关键词

**第三层：学生数据隔离**
- 学生调用NL2SQL时自动注入`student_scope`参数
- 生成的SQL自动追加`WHERE student_id = {current_user.id}`条件
- 学生只能查到自己的数据

**"删除所有数据"的具体处理**：
```python
# 用户输入: "删除所有客户数据"
# LLM生成: DELETE FROM crm_lead
# 安全校验: 检测到DELETE语句 → 拒绝执行
# 返回: {"error": "仅支持SELECT和UPDATE操作，不允许DELETE"}
```

---

### Q9：心理监测模块是怎么设计的？如何做到"无声"评估？

**答：**

心理监测采用**主动+被动**双轨机制：

**主动评估**（意图为`psych_care`时）：
1. LLM深度评估：分析用户文本，输出`emotion_tag`/`emotion_score`/`risk_level`
2. 分级回复：high→极度温和+建议专业帮助，medium→共情+小建议，low→轻松鼓励

**被动评估**（全局，任何意图都触发）：
- 在处理完用户意图后，额外附加轻量心理评估
- 返回结果中包含`psych_alert`字段（如有风险）
- 不影响主流程响应时间

**关键词快速检测**（不调用LLM，毫秒级）：
- **高危词（14个）**：不想活/想死/自杀/跳楼/割腕/活不下去/了结/解脱...
- **中危词（28个）**：崩溃/失眠/想家/孤独/抑郁/焦虑/压力很大/撑不下去...

**预警触发流程**：
```
检测到高危词 → risk_level=high
  → 写入 StudentPsychAlert 表
  → 更新 StudentPsychProfile（累计预警次数+1）
  → 返回极度温和回复 + 建议联系专业帮助
  → 定时任务：每周一生成心理周报，高危学生通知班主任
```

**数据闭环**：心理画像（`StudentPsychProfile`）持续更新，`total_risk_count`累计记录，班主任可查看`teacher_follow_up_status`跟进状态。

---

### Q10：对话状态管理如何处理并发和超时？

**答：**

`ConversationStateManager`采用内存字典+TTL机制：

**并发处理**：
- 以`session_id`（用户ID+Agent类型组合）为key，不同用户/不同Agent互不干扰
- 同一用户在客服Agent和企业助手的对话状态独立管理

**超时机制**：
- 每个会话状态创建时记录`created_at`时间戳
- TTL=600秒（10分钟），超时后视为新对话
- 每次交互自动更新`last_active`，延长有效时间

**异常处理**：
- 话题切换检测：识别"算了/取消/换个话题"等关键词，清除当前状态
- 确认阶段短输入检测：用户回复"是/对/确认"时识别为确认而非新输入
- 交互次数上限：MAX_INTERTRACTIONS=5，超限后主动终止槽位填充

**局限性与改进方向**：
- 当前为内存存储，服务重启后状态丢失
- 生产环境应迁移到Redis，支持分布式和持久化

---

## 三、数据库与后端设计（4题）

### Q11：你的CRUD层是怎么设计的？有没有遇到N+1查询问题？

**答：**

CRUD层按**业务领域**拆分为12个CRUD类，每个类封装一张表或一组关联表的全部操作：

| CRUD类 | 职责 | 核心方法 |
|--------|------|---------|
| UserCRUD | 用户增删改查 | get_by_username, validate_head_teacher |
| CrmCRUD | 意向客户管理 | create, get_all(支持status筛选), update |
| EventCRUD | 活动讲座 | register(自动+1当前人数), get_registrations |
| StudentServiceCRUD | 请假管理 | create_leave(含防重复提交) |
| FeedbackCRUD | 投诉反馈 | resolve(更新状态+记录解决方案) |
| NotificationCRUD | 站内通知 | mark_read, mark_all_read, get_unread_count |
| AcademicCRUD | 教务信息 | get_upcoming(未来N天未完成DDL) |
| StudyAbroadCRUD | 留学进度 | get_by_student, get_current_stage |
| PsychAlertCRUD | 心理预警 | create, update_profile(更新/创建画像) |
| ReportCRUD | 员工日报 | create, get_all(支持员工筛选) |
| ScoreCRUD | 学生成绩 | create, get_by_student, batch_create |
| OrgCRUD | 组织架构 | get_tree(递归构建树形), get_dept_members |

**N+1问题处理**：
- 仪表盘查询`DashboardCRUD.get_stats()`使用聚合查询，一次查出4项统计
- 组织架构树`OrgCRUD.get_tree()`先全量查询再内存递归构建，避免N+1
- 当前数据量小（百级），N+1问题不显著；如数据量增大，可通过`joinedload`或子查询优化

---

### Q12：JWT认证的权限控制是怎么设计的？学生能不能看到其他学生的数据？

**答：**

采用**三层权限控制**：

| 层级 | 机制 | 实现 |
|------|------|------|
| 认证 | JWT Bearer Token | `get_current_user`依赖注入，解析token获取用户 |
| 授权 | 角色校验 | `require_student`/`require_employee_or_admin`限定角色 |
| 数据隔离 | 自有数据校验 | `enforce_self_only`确保学生只能操作自己的数据 |

**`enforce_self_only`实现**：
```python
def enforce_self_only(current_user, target_user_id: int) -> None:
    if current_user.user_type == "STUDENT" and current_user.id != target_user_id:
        raise HTTPException(status_code=403, detail="仅可查看/操作自己的数据")
```

**具体场景**：
- 学生查询成绩：`GET /api/enterprise/score?student_id=7` → 学生7只能传7，传8则403
- 学生查询通知：`GET /api/student/notification?recipient_id=7` → 同上
- 员工/管理员不受限制：可查任何学生的数据

**Token机制**：
- 密钥：HS256签名，Secret Key从配置文件加载
- 有效期：1440分钟（24小时）
- Payload：`{"sub": "用户ID", "exp": 过期时间}`
- 401自动处理：前端`api.js`检测到401时自动清除token并跳转登录页

---

### Q13：软删除是怎么实现的？为什么不直接物理删除？

**答：**

所有15张表都有`delete_flag`字段（0=正常，1=已删除）。

**实现方式**：
- **查询时过滤**：所有CRUD查询都加`delete_flag == 0`条件
- **删除时标记**：`UserCRUD.delete()`将`delete_flag`设为1而非`DELETE`
- **唯一约束兼容**：`username`等唯一字段在软删除后允许重新注册同名账号

**选择软删除的理由**：
1. **数据安全**：误删可恢复，CRM客户数据不可丢失
2. **审计追踪**：保留完整操作记录，满足合规要求
3. **外键兼容**：关联数据（如请假记录引用student_id）不会因学生"删除"而断链
4. **业务需要**：已流失客户的历史数据仍有分析价值

**当前不足**：
- 唯一字段（如username）软删除后，新注册同名用户可能冲突
- 改进方案：删除时追加`_deleted_{timestamp}`后缀，或使用复合唯一索引

---

### Q14：定时任务调度器做了什么？对业务有什么价值？

**答：**

基于APScheduler的`BackgroundScheduler`，3个定时任务：

| 任务 | 时间 | 功能 | 业务价值 |
|------|------|------|---------|
| DDL提醒 | 每天09:07 | 检查未来N天待完成教务事项，根据`remind_days_before`配置推送通知 | 防止学生错过考试/作业截止日期 |
| 周报生成 | 每周一09:17 | 自动生成心理周报+投诉周报；高危学生通知班主任 | 早期发现心理问题，及时干预 |
| 跟进提醒 | 每天15:07 | 超3天未处理投诉→提醒班主任；超2天未审批请假→提醒班主任 | 避免投诉/请假被遗漏，提升服务响应速度 |

**通知闭环设计**：
- 审批通过/驳回 → 自动给学生发通知
- 投诉提交 → 给管理员+班主任发通知
- 投诉处理 → 给学生发确认通知
- 心理预警 → 记入画像 + 周报汇总 + 班主任提醒

---

## 四、前端与交互设计（3题）

### Q15：前端为什么不用Vue/React？Hash路由有什么优缺点？

**答：**

**不用框架的理由**：
1. **演示场景**：项目核心价值在AI Agent对话能力，前端是展示载体而非产品本身
2. **部署简单**：纯静态文件，无需Node.js构建，FastAPI直接托管
3. **上手门槛低**：团队成员无需学习框架，纯JS即可维护
4. **体量小**：25个JS文件共约3000行，框架反而过重

**Hash路由（`#/dashboard`）的优缺点**：

| 优点 | 缺点 |
|------|------|
| 无需服务端配置支持SPA | URL不够美观（带#号） |
| 浏览器原生支持`hashchange` | 不利于SEO（本项目不需要） |
| 刷新不会404 | 无法利用HTML5 History API的高级特性 |

**路由守卫实现**：
- `requireAuth`标记：未登录用户访问需认证页面时重定向到`/login`
- 角色菜单过滤：侧边栏根据`user_type`动态展示，ADMIN看到全部菜单

---

### Q16：前端的三种角色视图是怎么区分的？如何保证一个人只看到自己该看的？

**答：**

**菜单级别**：`sidebar.js`定义菜单项时指定`roles`数组，渲染时根据`user_type`过滤：

| 菜单分组 | ADMIN | EMPLOYEE | STUDENT |
|---------|-------|----------|---------|
| 仪表盘 | ✅ | ✅ | ✅ |
| 客服（活动/项目/画像/文件） | ✅ | ✅ | ❌ |
| 企业（CRM/日报/成绩/员工/审批/架构） | ✅ | ✅ | ❌ |
| 学生（教务/留学/请假/反馈/通知） | ✅ | ❌ | ✅ |

**数据级别**：
- API请求携带JWT Token，后端`enforce_self_only`校验
- 前端查询参数自动填充当前用户ID（如学生查成绩时`student_id`取自localStorage）

**UI级别**：
- 仪表盘：EMPLOYEE显示4张统计卡（客户/日报/审批/活动），STUDENT显示4张统计卡（DDL/留学/通知/成绩）
- 聊天Agent：EMPLOYEE/ADMIN→企业助手，STUDENT→学生助手，未登录→客服助手
- 操作按钮：审批页面仅班主任角色显示"通过/驳回"按钮

---

### Q17：活动报名的并发安全是怎么处理的？如果两人同时报名最后一个名额怎么办？

**答：**

**当前实现**（`EventCRUD.register`）：
```python
# 1. 查询当前人数
event = db.query(EventLecture).filter(EventLecture.id == event_id).first()
# 2. 判断是否已满
if event.max_participants and event.current_participants >= event.max_participants:
    raise HTTPException(status_code=400, detail="报名已满")
# 3. 创建报名记录 + current_participants += 1
```

**并发问题**：两个请求同时读到`current_participants=99`（max=100），都判断未满，都写入，最终变成101人。

**SQLite下的天然保护**：
- SQLite使用文件级锁，写操作串行化，极端并发场景下实际不会出现
- 开发/演示环境足够安全

**MySQL生产环境改进方案**：
1. **乐观锁**：`UPDATE event_lecture SET current_participants = current_participants + 1 WHERE id = ? AND current_participants < max_participants`，检查affected rows
2. **数据库约束**：添加CHECK约束`current_participants <= max_participants`
3. **Redis原子计数**：`INCR` + Lua脚本保证原子性
4. **分布式锁**：活动ID加锁，串行处理报名请求

---

## 五、AI能力深度追问（4题）

### Q18：LLM调用失败或超时怎么办？有没有降级方案？

**答：**

**当前降级策略**：

| Agent | 降级方案 |
|-------|---------|
| 客服Agent | 关键词匹配FAQ + 本地默认回复 |
| 企业助手 | NL2SQL失败→提示"请用更明确的描述"；日报摘要失败→返回原文 |
| 学生助手 | 心理评估失败→关键词快速检测兜底；请假提取失败→提示手动填写 |

**具体实现**：
- `LLMClient`调用使用`try-except`包裹，超时/异常时返回None
- Agent检测到None后走本地fallback逻辑
- 客服闲聊：预设20+本地回复模板（"我是小粤，粤教服务的智能助手..."）
- 企业闲聊：关键词匹配回复（"谢谢"/"不客气"等）

**超时配置**：`openai_max_tokens=2000`限制响应长度，间接控制延迟。

---

### Q19：画像研判的打分规则是怎么设计的？50分的阈值怎么定的？

**答：**

**评分体系**（`assess_lead_intention`函数，`file_parser.py`）：

**新加坡项目评分**（总分约100）：

| 维度 | 条件 | 分值 | 理由 |
|------|------|------|------|
| 年龄 | 14-16岁 | +30 | 匹配2+2本科班目标人群 |
| 年龄 | 16-19岁 | +30 | 匹配0.5+2本科班目标人群 |
| 年龄 | 17+且中职 | +25 | 匹配大专就业班 |
| 学历 | 匹配项目要求 | +25 | 核心筛选维度 |
| 意向国家 | 新加坡 | +15 | 明确意向 |
| 家庭经济 | 良好 | +10 | 留学需要经济基础 |
| 语言水平 | 有等级 | +5 | 加分项 |
| 年龄+学历双匹配 | 同时匹配 | +15 | 强信号 |

**德国项目评分**（总分约100）：

| 维度 | 条件 | 分值 |
|------|------|------|
| 年龄 | 18-35岁 | +25 |
| 学历 | 高中及以上 | +20 |
| 意向国家 | 德国 | +15 |
| 德语水平 | 有等级 | +15 |
| 家庭经济 | 一般/良好 | +10 |
| 年龄+学历双匹配 | 同时匹配 | +15 |

**50分阈值的考量**：
- 低于50分：仅1-2个弱信号匹配，意向不明确，暂不入CRM
- 50-70分：基本匹配，建议跟进，录入CRM标记"新增意向"
- 70分以上：高度匹配，优先跟进，可标记"高意向"

**意向国家过滤**：如果明确指定了意向国家，另一国项目评分清零，避免推荐不相关项目。

---

### Q20：知识库有多少条数据？检索效果如何评估？有没有Bad Case？

**答：**

**知识库统计**：

| 类别 | 文件数 | QA条数 |
|------|--------|--------|
| 公司业务 | 2 | 58 |
| 留学政策 | 2 | 108 |
| 公司信息 | 3 | 117 |
| 用户研判规则 | 1 | 1(示例) |
| **合计** | **8** | **283** |

**检索效果评估**：

| 场景 | 效果 | 说明 |
|------|------|------|
| 精确关键词匹配 | 好 | "新加坡2+2学费"能精准命中 |
| 同义词匹配 | 较好 | "多少钱"→"学费"，52条映射覆盖常见口语 |
| 语义相似但词不同 | 一般 | "毕业后能留当地吗"可能召回不了"PR/永居"相关 |
| 多跳推理 | 差 | "我在广州，高中毕业，想读本科，预算30万"需综合匹配 |

**典型Bad Case**：
- 用户问"宿舍怎么样"→ 知识库无宿舍相关QA，RAG检索为空
- 用户问"英语不好能去新加坡吗"→ 需要语义理解而非关键词匹配

**改进方向**：
1. 扩充知识库QA条数至500+
2. 引入向量检索（text2vec-base-chinese）作为Rerank层
3. 用户反馈机制：检索结果下方增加"有帮助/无帮助"按钮

---

### Q21：语音日报的实现原理是什么？从口述到结构化日报经历了哪些步骤？

**答：**

`VoiceProcessor.text_to_report()`的处理流程：

```
口述文本: "今天去拜访了张三家长，他们对新加坡项目很感兴趣，
          准备下周来公司详细咨询。下午整理了3个客户资料。"
          ↓
Step 1: LLM提取工作类型
  → "客户拜访"
          ↓
Step 2: LLM生成结构化摘要
  → {
      "work_type": "客户拜访",
      "summary": "拜访张三家长，意向新加坡项目，下周来公司咨询；整理3个客户资料"
    }
          ↓
Step 3: 返回结构化日报数据，前端展示
```

**语音输入的完整链路**（当前Whisper部分为占位实现）：
```
语音文件 → Whisper API转文字 → text_to_report() → 结构化日报
```

**周报汇总**（`summarize_reports()`）：
```
多份日报 → LLM汇总 → Markdown格式周报
  包含：本周工作概述/重点事项/下周计划
```

---

## 六、安全与工程实践（3题）

### Q22：系统有哪些安全措施？如果部署到公网还需要做什么？

**答：**

**已有安全措施**：

| 措施 | 实现 |
|------|------|
| 密码安全 | bcrypt哈希（截断72字节），不存明文 |
| 传输安全 | JWT Bearer Token，HS256签名 |
| 权限控制 | 三层：认证→授权→数据隔离 |
| SQL注入 | SQLAlchemy ORM参数化查询 |
| NL2SQL安全 | 白名单+结构校验+学生数据隔离 |
| CORS | 可配置允许的域名 |

**部署到公网必须做的**：

| 优先级 | 措施 | 说明 |
|--------|------|------|
| P0 | HTTPS | 全站HTTPS，防止Token被窃听 |
| P0 | 更换Secret Key | 当前硬编码在config.py，必须换为随机强密钥 |
| P0 | CORS限制 | 将`*`改为具体域名 |
| P1 | 速率限制 | 防止暴力破解登录和API滥用 |
| P1 | 日志脱敏 | 手机号/身份证/密码等敏感信息不记入日志 |
| P1 | 数据库连接加密 | MySQL使用SSL连接 |
| P2 | WAF | 防XSS/CSRF/SQL注入 |
| P2 | 文件上传安全 | 限制文件类型/大小/病毒扫描 |
| P2 | Token刷新机制 | Access Token短过期+Refresh Token |

---

### Q23：你是怎么做测试的？测试覆盖率如何？

**答：**

项目有`tests/`目录，包含：

**已有测试**：
- API接口测试：验证各端点请求/响应格式
- 认证测试：JWT生成/解析/过期处理
- CRUD测试：数据库增删改查
- `test_check.db`/`test.db`：SQLite测试数据库

**测试方法**：
- FastAPI的`TestClient`做集成测试
- 使用独立的SQLite测试数据库，不污染开发数据
- `pytest.ini`配置测试环境

**不足与改进**：
- 缺少Agent意图分类的单元测试
- 缺少并发场景的压力测试
- 缺少RAG检索效果的回归测试
- 测试覆盖率未统计（建议引入`pytest-cov`）
- 前端无自动化测试

---

### Q24：如果让你继续优化这个项目，你会优先做哪三件事？

**答：**

**P0：修复前后端API不匹配问题**

当前发现多处不匹配：
- `profileMatch.js`用GET调用，后端是POST
- `notifications.js`标记已读用GET，后端是PUT
- 这些Bug导致功能完全不可用

修复方案：统一前端API调用方法，或后端同时支持GET/POST。

**P1：前端交互体验升级**

当前问题：
- 新增/修改数据后页面不自动刷新
- 缺少加载状态和骨架屏
- 空数据无友好提示
- 错误提示不够直观

改进方案：
- 所有写操作成功后自动重新加载列表
- 添加`API.request`全局loading状态
- 空状态占位图+提示文案
- Toast错误提示展示后端具体错误信息

**P2：智能报告和NL2SQL前端化**

后端已有5类AI报告和NL2SQL接口，但前端未对接：
- 新增"数据查询"页面：输入自然语言→展示查询结果表格
- 新增"智能报告"页面：客户月报/心理周报/投诉周报等
- 员工日报页面增加"AI摘要"展示

---

## 七、项目特色与亮点总结

### 核心亮点

1. **三Agent架构**：面向三类用户的9+10+9=28种意图路由，覆盖获客→管理→服务全链路
2. **槽位填充**：多轮对话收集结构化信息，替代传统表单交互
3. **NL2SQL双模式**：SELECT白名单查询+UPDATE白名单修改，兼顾灵活性和安全性
4. **心理监测**：主动+被动双轨评估，关键词毫秒级+LLM深度分析
5. **零依赖RAG**：283条QA+52条同义词映射，关键词+覆盖率检索，无需向量数据库
6. **全链路通知**：审批/投诉/请假→自动创建通知→定时任务催办
7. **客户研判**：文件上传自动解析→画像提取→评分→自动录入CRM
8. **软删除**：所有15张表统一软删除，保证数据安全和可恢复性

---

## 八、基础知识题（20题）

> 答辩老师常从项目中的具体技术点出发，追问底层原理和基础概念。以下问题均结合项目实际场景出题。

---

### Q25：什么是API？RESTful API的设计原则是什么？你的项目符合RESTful规范吗？

**答：**

**API（Application Programming Interface）**：应用程序编程接口，是软件系统之间交互的约定，定义了请求格式、响应格式和错误码。

**RESTful API设计原则**：

| 原则 | 说明 |
|------|------|
| 资源导向 | URL代表资源（名词），如`/api/enterprise/lead`代表意向客户 |
| HTTP方法语义化 | GET=查询，POST=创建，PUT=更新，DELETE=删除 |
| 无状态 | 每次请求包含所有必要信息（如JWT Token），服务器不保存会话状态 |
| 统一接口 | 相同的资源使用相同的URL模式 |
| 合适的状态码 | 200成功，400客户端错误，401未认证，403无权限，404不存在 |

**本项目的符合程度**：

| 方面 | 符合 | 不完全符合 |
|------|------|-----------|
| 资源导向URL | ✅ `/api/enterprise/lead`、`/api/student/leave` | |
| HTTP方法语义化 | ✅ GET查询、POST创建、PUT更新 | ❌ 审批接口用`POST /approvals/{id}/approve`而非`PUT /approvals/{id}` |
| 无状态 | ✅ JWT Token，每次请求携带 | |
| 状态码使用 | ✅ 200/400/401/403/404都有 | ❌ 部分错误返回200+success:false而非4xx |
| 响应格式统一 | | ❌ 有的返回`{success, message}`，有的返回`{leads: [...]}`，格式不完全统一 |

---

### Q26：什么是JWT？它和Session-Cookie认证有什么区别？各自的优缺点？

**答：**

**JWT（JSON Web Token）**：一种开放标准（RFC 7519），以紧凑的URL安全方式在各方之间传递声明信息。由三部分组成：

```
Header.Payload.Signature
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzQ3NDU2MDAwfQ.abc123signature
```

| 部分 | 内容 | 说明 |
|------|------|------|
| Header | `{"alg":"HS256","typ":"JWT"}` | 算法和类型 |
| Payload | `{"sub":"7","exp":1747456000}` | 用户ID和过期时间 |
| Signature | HMACSHA256(base64(header)+"."+base64(payload), secret) | 防篡改签名 |

**JWT vs Session-Cookie对比**：

| 维度 | JWT（本项目使用） | Session-Cookie |
|------|-----------------|----------------|
| 存储位置 | 客户端（localStorage） | 服务端（内存/Redis/数据库） |
| 状态 | 无状态，服务器不保存 | 有状态，服务器保存Session |
| 扩展性 | 天然支持分布式 | 需要Session共享（Redis等） |
| 安全性 | Token泄露无法主动失效 | 服务端可随时销毁Session |
| 跨域 | 天然支持（Bearer Token） | 需要CORS+Cookie配置 |
| 注销 | 只能等过期（本项目24小时） | 立即生效 |

**本项目的JWT实现**：
- 算法：HS256（对称加密，同一密钥签名和验证）
- 有效期：1440分钟（24小时）
- Token存储：前端`localStorage`中的`access_token`
- 认证流程：`Authorization: Bearer <token>` → FastAPI依赖注入`get_current_user`解析

---

### Q27：什么是ORM？SQLAlchemy相比原生SQL有什么优势和劣势？

**答：**

**ORM（Object-Relational Mapping，对象关系映射）**：将数据库表映射为编程语言的类，将表的行映射为对象，将列映射为属性，通过操作对象来操作数据库。

**本项目示例**：
```python
# ORM方式（本项目使用）
user = db.query(SysUser).filter(SysUser.id == 7).first()
user.real_name = "新名字"  # 修改属性
db.commit()                  # 自动生成UPDATE语句

# 等价的原生SQL
# SELECT * FROM sys_user WHERE id = 7
# UPDATE sys_user SET real_name = '新名字' WHERE id = 7
```

**优势 vs 劣势**：

| 优势 | 劣势 |
|------|------|
| 防SQL注入（参数化查询） | 复杂查询性能不如手写SQL |
| 数据库切换简单（SQLite→MySQL） | 生成SQL可能不优（如N+1问题） |
| 代码可读性高，面向对象思维 | 学习成本高 |
| 自动类型转换（Python↔数据库类型） | 调试困难（需看生成SQL） |
| 关联关系自动处理 | 过度抽象可能隐藏问题 |

**本项目选用SQLAlchemy的理由**：
1. 支持`db_type`动态切换SQLite/MySQL
2. 软删除过滤（`delete_flag==0`）可封装为基类方法统一处理
3. FastAPI与SQLAlchemy配合成熟，依赖注入集成方便

---

### Q28：什么是SPA？和传统多页面应用有什么区别？

**答：**

**SPA（Single Page Application，单页应用）**：整个应用只有一个HTML页面，通过JavaScript动态替换内容区域实现页面切换，无需整页刷新。

**本项目就是SPA**：`templates/index.html`是唯一的HTML文件，路由通过`router.js`的Hash路由实现。

| 维度 | SPA（本项目） | 传统多页面（MPA） |
|------|-------------|----------------|
| 页面加载 | 首次加载全部资源，后续只更新内容区 | 每次导航都整页刷新 |
| 路由 | 前端Hash路由（`#/dashboard`） | 后端路由（`/dashboard`） |
| 用户体验 | 无白屏闪烁，类原生App | 每次跳转有短暂白屏 |
| SEO | 不利于搜索引擎爬取 | 天然利于SEO |
| 首屏速度 | 慢（加载所有JS） | 快（只加载当前页） |
| 开发复杂度 | 前后端分离，需要路由管理 | 简单直接 |
| 部署 | 静态文件即可 | 需要服务端渲染 |

**本项目的SPA实现**：
- `index.html`加载所有25个JS文件
- `Router.register(path, renderFn, meta)`注册16条路由
- `Router.navigate(path)`触发页面切换：清空`#content` → 调用`render()`获取HTML → 填入DOM → 调用`onMount()`绑定事件

---

### Q29：什么是CORS？你的项目为什么需要配置CORS？

**答：**

**CORS（Cross-Origin Resource Sharing，跨域资源共享）**：浏览器安全策略，限制一个域名的网页向另一个域名的服务器发送请求。

**跨域的定义**：协议+域名+端口任一不同即为跨域。

```
前端: http://localhost:5500 (VSCode Live Server)
后端: http://localhost:8000 (FastAPI)
→ 端口不同 → 跨域 → 浏览器阻止请求
```

**本项目CORS配置**（`main.py`）：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # 允许所有来源
    allow_credentials=True,   # 允许携带Cookie
    allow_methods=["*"],      # 允许所有HTTP方法
    allow_headers=["*"],      # 允许所有请求头
)
```

**为什么需要CORS**：
- 前端和后端端口不同（开发环境），浏览器会发送预检请求（OPTIONS）
- 如果不配置CORS，前端`fetch`请求会被浏览器拦截，报CORS错误
- 生产环境应将`allow_origins`从`*`改为具体域名

**CORS工作流程**：
```
浏览器发送OPTIONS预检请求 → 服务器返回允许的来源/方法/头部
→ 浏览器判断允许 → 发送实际请求 → 服务器正常响应
```

---

### Q30：HTTP的GET、POST、PUT、DELETE分别是什么？什么时候用哪个？

**答：**

| 方法 | 语义 | 幂等性 | 安全性 | 本项目使用场景 |
|------|------|--------|--------|--------------|
| GET | 获取资源 | ✅幂等 | ✅安全 | 查询客户列表、查询成绩 |
| POST | 创建资源 | ❌非幂等 | ❌不安全 | 新增客户、提交请假、录入成绩 |
| PUT | 更新资源（全量替换） | ✅幂等 | ❌不安全 | 编辑客户信息、标记通知已读 |
| DELETE | 删除资源 | ✅幂等 | ❌不安全 | 删除课程项目（软删除） |

**幂等性**：多次调用效果相同。如`PUT /lead/1`更新客户1，调用1次和100次结果一样。而`POST /lead`每次调用都新增一条记录。

**安全性**：是否修改服务器数据。GET只读不写，所以安全；POST/PUT/DELETE会修改数据，不安全。

**本项目中的特殊用法**：
- `POST /approvals/{id}/approve`：严格来说审批是状态变更，应该用PUT，但项目中用POST也可以接受
- `PUT /notification/read-all`：标记全部已读，语义上是更新操作，用PUT正确
- 审批接口用POST是因为它有业务副作用（创建通知等），不仅仅是简单更新

---

### Q31：什么是bcrypt？为什么不用MD5或SHA256来存密码？

**答：**

**bcrypt**：一种专为密码存储设计的哈希算法，基于Blowfish密码，具有两个关键特性——**加盐（Salt）**和**慢速（Cost Factor）**。

**本项目实现**：
```python
def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")[:72]  # bcrypt限制72字节
    salt = bcrypt.gensalt()     # 自动生成随机盐
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")
```

**为什么不用MD5/SHA256**：

| 维度 | MD5 | SHA256 | bcrypt |
|------|-----|--------|--------|
| 设计目的 | 数据校验 | 数据校验 | 密码存储 |
| 速度 | 极快（GPU每秒10亿+） | 快（GPU每秒数亿） | 故意慢（可调成本因子） |
| 加盐 | 需手动 | 需手动 | 自动内置 |
| 彩虹表攻击 | 容易被攻破 | 需要较大彩虹表 | 盐不同，彩虹表无效 |
| 暴力破解 | 毫秒级 | 秒级 | 每次约100ms |

**核心原理**：
- **加盐**：每个密码用不同的随机盐，相同密码哈希值不同，彩虹表无效
- **慢速**：bcrypt计算耗时约100ms，GPU暴力破解成本极高（10万次/秒 vs MD5的10亿次/秒）
- **自适应**：可调整cost factor，硬件变快时增大cost保持破解难度

**72字节截断**：bcrypt设计限制最多72字节输入，超长密码截断处理。

---

### Q32：什么是FastAPI？它和Flask、Django有什么区别？

**答：**

**FastAPI**：基于Python 3.6+类型提示的现代Web框架，使用Starlette作为底层，Pydantic做数据校验。

| 维度 | FastAPI（本项目） | Flask | Django |
|------|-----------------|-------|--------|
| 性能 | 高（异步ASGI） | 中（同步WSGI） | 中（同步WSGI） |
| 自动文档 | ✅ Swagger/ReDoc | ❌ 需手动 | ❌ 需drf-spectacular |
| 类型校验 | ✅ Pydantic自动 | ❌ 手动 | ❌ 需Django Forms |
| 异步支持 | ✅ 原生async/await | ❌ 需要扩展 | ❌ Django 3.0+部分支持 |
| 依赖注入 | ✅ 内置 | ❌ 需要扩展 | ❌ 需要扩展 |
| ORM | 不绑定（本项目用SQLAlchemy） | 不绑定 | 内置Django ORM |
| 体积 | 轻量 | 轻量 | 全功能重量级 |
| 学习曲线 | 低 | 低 | 高 |

**本项目选择FastAPI的理由**：
1. **依赖注入**：`Depends(get_db)`自动管理数据库会话，`Depends(require_student)`自动校验权限
2. **自动文档**：`/docs`页面可直接测试所有API，演示时非常方便
3. **Pydantic校验**：请求体自动校验类型和必填字段，如`LeadCreateRequest`中`customer_name`必填
4. **异步能力**：文件上传等IO密集操作可用`async def`

---

### Q33：什么是Pydantic？它在项目中起到什么作用？

**答：**

**Pydantic**：Python数据校验库，使用Python类型注解定义数据模型，自动校验输入数据、序列化输出数据。

**本项目使用场景**：

**1. 请求体校验**（`schemas/schemas.py`）：
```python
class LeadCreateRequest(BaseModel):
    customer_name: str        # 必填，字符串类型
    contact_info: str = ""    # 可选，默认空字符串
    age: int | None = None    # 可选，整数或None
    intended_country: str = ""# 可选
```
→ 如果前端没传`customer_name`，Pydantic自动返回422错误：`"field required"`

**2. 配置管理**（`config.py`）：
```python
class Settings(BaseSettings):
    db_type: str = "mysql"          # 带默认值
    api_port: int = 8000            # 自动转为int
    model_config = {"env_file": ".env"}  # 自动从.env文件读取
```

**3. 响应序列化**：
```python
req.model_dump(exclude_none=True)  # 自动转为字典，排除None值
```

**核心优势**：
- 自动类型转换：`"8000"`字符串自动转`8000`整数
- 友好的错误信息：`"value is not a valid integer"`而非程序崩溃
- 与FastAPI深度集成：函数参数声明Pydantic模型，FastAPI自动校验

---

### Q34：什么是SQL注入？你的项目是怎么防止的？

**答：**

**SQL注入**：攻击者通过输入恶意SQL片段，改变原有SQL语义，执行未授权操作。

**经典攻击示例**：
```python
# 危险写法（字符串拼接）
username = request.get("username")  # 用户输入: ' OR 1=1 --
sql = f"SELECT * FROM sys_user WHERE username = '{username}'"
# 实际执行: SELECT * FROM sys_user WHERE username = '' OR 1=1 --'
# 结果: 返回所有用户数据！
```

**本项目的防护措施**：

**1. SQLAlchemy ORM参数化查询**（主要防护）：
```python
# 安全写法（参数化查询）
user = db.query(SysUser).filter(SysUser.username == username).first()
# 生成SQL: SELECT * FROM sys_user WHERE username = ?  参数: ['admin']
# 无论输入什么，都只作为参数值处理，不会被解释为SQL语法
```

**2. Pydantic类型校验**：
- 请求体字段有明确类型（`str`/`int`/`date`），异常输入在入口就被拦截
- 如`student_id: int`，传入字符串会被Pydantic返回422错误

**3. NL2SQL的特殊防护**：
- 白名单：只允许查/改特定表和列
- 结构校验：必须有WHERE和LIMIT
- 危险关键词检测：DROP/DELETE/INSERT等

---

### Q35：什么是依赖注入？FastAPI的`Depends`是怎么工作的？

**答：**

**依赖注入（Dependency Injection，DI）**：一种设计模式，将组件所需的依赖从外部传入，而不是在组件内部创建。核心思想是"不要自己造，让别人给你"。

**本项目大量使用的FastAPI依赖注入**：

```python
# 1. 数据库会话注入
@router.get("/api/student/leave")
def list_leaves(db: Session = Depends(get_db)):
    # 不需要自己创建db，FastAPI自动调用get_db()注入
    ...

# 2. 认证依赖注入
@router.post("/api/student/leave")
def create_leave(req: LeaveCreateRequest, db: Session = Depends(get_db),
                  current_user: SysUser = Depends(require_student)):
    # require_student自动: 解析Token → 查用户 → 校验角色 → 注入用户对象
    # 如果Token无效 → 自动返回401
    # 如果角色不对 → 自动返回403
    ...

# 3. 依赖的嵌套
def require_student(current_user = Depends(get_current_user)):
    # get_current_user本身也是依赖
    if current_user.user_type != "STUDENT":
        raise HTTPException(403)
    return current_user

def get_current_user(credentials = Depends(security), db = Depends(get_db)):
    # security提取Token → db查用户 → 返回用户对象
    ...
```

**执行流程**：
```
请求到达 → FastAPI解析函数签名
  → 发现Depends(get_db) → 调用get_db() → 获取数据库会话
  → 发现Depends(require_student) → 调用require_student()
    → 内部依赖get_current_user()
      → 内部依赖security → 提取Token
      → 内部依赖get_db → 获取数据库会话
      → 解析Token → 查用户 → 校验角色
  → 所有依赖解析完毕 → 调用实际函数
```

**优势**：代码复用（认证逻辑写一次），测试方便（可替换依赖），关注点分离。

---

### Q36：什么是中间件？项目中的CORS中间件是怎么工作的？

**答：**

**中间件（Middleware）**：在请求到达路由处理函数之前和响应返回客户端之后执行的拦截器，类似"过滤器"或"管道"。

**中间件的洋葱模型**：
```
请求 → [CORS中间件 → 日志中间件 → ...] → 路由处理函数
响应 ← [CORS中间件 ← 日志中间件 ← ...] ← 路由处理函数
```

**本项目CORS中间件的工作流程**：

```
1. 浏览器发送OPTIONS预检请求
   ↓
2. CORS中间件拦截OPTIONS请求
   ↓
3. 检查请求头Origin是否在allow_origins列表中
   ↓ (本项目allow_origins=["*"]，即允许所有)
4. 添加响应头：
   Access-Control-Allow-Origin: *
   Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
   Access-Control-Allow-Headers: Authorization, Content-Type
   Access-Control-Allow-Credentials: true
   ↓
5. 返回200，浏览器根据响应头判断是否允许实际请求
   ↓
6. 浏览器发送实际请求（GET/POST等）
   ↓
7. CORS中间件在响应中同样添加上述头
   ↓
8. 浏览器检查响应头，允许JS读取响应数据
```

**如果不配置CORS中间件**：浏览器报错`"Access to fetch has been blocked by CORS policy"`，前端完全无法调用后端API。

---

### Q37：什么是SQLite和MySQL？你的项目为什么支持两种数据库？

**答：**

| 维度 | SQLite（开发环境） | MySQL（生产环境） |
|------|-------------------|-------------------|
| 类型 | 嵌入式文件数据库 | 客户端-服务器数据库 |
| 部署 | 零配置，单文件`yuejiao.db` | 需安装MySQL服务，配置用户/权限 |
| 并发 | 读并发好，写串行（文件级锁） | 高并发读写（行级锁+事务） |
| 性能 | 小数据量足够 | 大数据量+高并发优秀 |
| 适用场景 | 开发/测试/演示/单机应用 | 生产环境/多人并发访问 |
| 数据量 | 百万级以下 | 亿级以上 |

**项目双数据库支持**（`config.py`）：
```python
@property
def database_url(self) -> str:
    if self.db_type.lower() == "sqlite":
        return self.sqlite_url  # sqlite:///./yuejiao.db
    return f"mysql+pymysql://..." # MySQL连接串
```

**切换方式**：修改`.env`文件中的`DB_TYPE=sqlite`或`DB_TYPE=mysql`即可。

**为什么支持两种**：
1. **开发效率**：SQLite零配置，`python main.py`即可启动，不依赖外部服务
2. **演示便携**：数据库是一个文件，拷贝即可迁移
3. **生产就绪**：部署时切换MySQL，获得高并发和事务支持
4. **SQLAlchemy抽象**：ORM层屏蔽了SQL方言差异，切换代价极低

---

### Q38：什么是RAG？它和大模型直接回答有什么区别？

**答：**

**RAG（Retrieval-Augmented Generation，检索增强生成）**：先从知识库中检索相关文档，再将检索结果作为上下文喂给大模型生成回答。

**对比**：

| 维度 | 大模型直接回答 | RAG（本项目使用） |
|------|-------------|-----------------|
| 知识来源 | 训练数据（截止日期前的公开数据） | 实时检索私有知识库 |
| 事实准确性 | 可能"幻觉"编造事实 | 基于检索到的事实，更准确 |
| 私有数据 | 无法回答公司内部信息 | 可以回答公司业务/政策等 |
| 可更新性 | 需重新训练 | 更新知识库即可，无需训练 |
| 成本 | 每次调用消耗Token | 检索+生成，Token更少 |
| 可追溯性 | 不知道答案来源 | 可标注答案来自哪个文档 |

**本项目RAG的实际应用**：
```
用户: "新加坡2+2本科的学费是多少？"
  ↓ Step 1: 检索知识库
  → 命中QA: "新加坡2+2本科总学费约30-31万"
  ↓ Step 2: 构造Prompt
  → "请根据以下参考信息回答用户问题：[检索结果]"
  ↓ Step 3: LLM生成回答
  → "新加坡2+2本科班总学费约30-31万元，包含国内2年+新加坡2年..."
```

**不使用RAG的问题**：
- 大模型不知道"粤教服务"这家公司的信息
- 不知道具体的学费数字和报名流程
- 可能编造不存在的项目信息

---

### Q39：什么是意图识别？你的项目是怎么做的？

**答：**

**意图识别（Intent Classification）**：自然语言理解的核心任务，判断用户输入属于哪个预定义的意图类别。

**传统方法 vs LLM方法**：

| 维度 | 传统方法（规则/SVM/BERT） | LLM方法（本项目） |
|------|------------------------|-----------------|
| 训练数据 | 需要大量标注数据 | Few-shot，只需几个示例 |
| 新增意图 | 需重新训练模型 | 修改Prompt即可 |
| 准确率 | 专用模型更精准 | 依赖Prompt质量 |
| 延迟 | 低（毫秒级） | 较高（秒级，需调LLM） |
| 灵活性 | 低（固定类别） | 高（自然语言定义意图） |

**本项目的意图识别流程**：
```
用户输入: "我想请假回家"
  ↓
Step 1: 短输入预检（<4字）
  "请假" → 关键词表命中 → 直接路由到admin_service
  ↓ (如果短输入未命中)
Step 2: 构造Prompt
  "以下是学生助手的意图列表：[9种意图及描述]
   用户输入：'我想请假回家'
   请判断用户意图，输出JSON：{intent: '...'}"
  ↓
Step 3: LLM输出
  {intent: "admin_service"}
  ↓
Step 4: 路由到对应处理器
  _handle_admin_service()
```

**本项目3个Agent共28种意图**：客服9种、企业10种、学生9种。

---

### Q40：什么是Token？大模型的Token和JWT的Token是同一个东西吗？

**答：**

**完全不同的两个概念**，只是英文单词相同：

| 维度 | JWT Token（认证用） | LLM Token（大模型用） |
|------|-------------------|---------------------|
| 本质 | 加密字符串，用于身份认证 | 文本的最小语义单元，用于计费 |
| 格式 | Header.Payload.Signature | 数字ID（如token_id=1234） |
| 生命周期 | 创建后24小时内有效 | 模型推理时临时使用 |
| 作用 | 证明"我是谁" | 计算"用了多少字" |
| 本项目用途 | `Authorization: Bearer <jwt>` | `openai_max_tokens=2000`限制回复长度 |

**LLM Token详解**：

大模型不是按"字"处理文本，而是按"Token"处理。1个Token大约对应：
- 英文：1个单词 ≈ 1-2个Token
- 中文：1个汉字 ≈ 1-3个Token

**示例**：
```
"新加坡2+2本科" → Token化 → [新, 加, 坡, 2, +, 2, 本, 科] → 约8个Token
```

**本项目中Token相关的配置**：
```python
# config.py
openai_max_tokens: int = 2000     # LLM单次回复最多2000个Token
openai_temperature: float = 0.7   # 生成随机性（0=确定，1=随机）
```

**计费影响**：OpenAI按Token数量计费，输入+输出Token都收费。本项目单次对话约消耗500-2000 Token。

---

### Q41：什么是软删除？和物理删除有什么区别？

**答：**

| 维度 | 物理删除（DELETE） | 软删除（Soft Delete，本项目使用） |
|------|-------------------|-------------------------------|
| 操作 | `DELETE FROM table WHERE id=1` | `UPDATE table SET delete_flag=1 WHERE id=1` |
| 数据 | 永久消失 | 仍在数据库中，只是标记为删除 |
| 恢复 | 不可能 | 改回`delete_flag=0`即可恢复 |
| 查询 | 直接查 | 需加`WHERE delete_flag=0` |
| 存储空间 | 释放 | 占用（但可定期清理） |
| 外键 | 可能破坏关联（学生删了，请假记录怎么办？） | 不影响（学生标记删除，请假记录仍可查） |

**本项目软删除实现**：
```python
# 所有15张表都有这个字段
delete_flag = Column(SmallInteger, default=0, comment='软删除 0=正常 1=删除')

# 查询时统一过滤
user = db.query(SysUser).filter(SysUser.id == user_id, SysUser.delete_flag == 0).first()
```

**实际业务场景**：
- 客户"王五"标记为"已流失"→ 不应该物理删除，历史跟进记录仍有分析价值
- 学生退学 → 标记删除，但成绩/请假记录需要保留用于审计
- 误删恢复 → `UPDATE sys_user SET delete_flag=0 WHERE id=7`

---

### Q42：什么是前后端分离？你的项目是前后端分离吗？

**答：**

**前后端分离**：前端负责UI展示和交互，后端负责业务逻辑和数据处理，通过API通信，各自独立开发、部署。

| 维度 | 传统模板渲染 | 前后端分离（本项目） |
|------|------------|-------------------|
| 后端职责 | 渲染HTML+业务逻辑 | 纯API，返回JSON |
| 前端职责 | 无（浏览器直接显示HTML） | 渲染UI+交互逻辑 |
| 通信方式 | 无（服务端直接输出HTML） | HTTP API（JSON） |
| 前端技术 | 模板引擎（Jinja2） | 独立JS/CSS/HTML |
| 开发效率 | 前后端耦合 | 可并行开发 |
| 复用性 | 只能用于Web | 同一API可供App/小程序调用 |

**本项目的前后端分离情况**：

| 方面 | 分离 | 不完全分离 |
|------|------|-----------|
| API返回JSON | ✅ 所有接口返回JSON | |
| 前端独立渲染 | ✅ JS动态渲染页面 | |
| 部署独立 | ❌ 前端由FastAPI的StaticFiles托管 | |
| 开发独立 | ❌ 前端在同一个Git仓库 | |

**不是完全的前后端分离**：前端静态文件由FastAPI直接托管（`app.mount("/static", StaticFiles(...))`)，而非部署在Nginx或CDN。这在演示阶段足够，生产环境应前后端独立部署。

---

### Q43：什么是Prompt Engineering？你在项目中是怎么设计Prompt的？

**答：**

**Prompt Engineering（提示词工程）**：设计和优化输入给大模型的文本，以引导模型产生期望输出的技术。

**本项目中的Prompt设计示例**（意图分类）：

```
你是一个意图分类器。请根据用户输入判断意图，输出JSON格式。

可用意图列表：
- admin_service: 请假、考务等行政服务
- psych_care: 心理关怀、情绪疏导
- feedback: 投诉、建议、咨询
- academic_query: 学业、考试、DDL查询
- progress_track: 留学进度查询
- life_support: 海外生活支持
- upgrade_intent: 升学、项目推荐
- data_query: 数据查询
- chitchat: 闲聊

示例：
输入："我想请假" → {"intent": "admin_service"}
输入："最近压力好大" → {"intent": "psych_care"}
输入："考试什么时候" → {"intent": "academic_query"}

用户输入：{user_input}
```

**Prompt设计原则**（本项目实践）：
1. **角色设定**："你是一个意图分类器"→ 引导模型进入分类模式
2. **输出格式约束**："输出JSON格式"→ 确保可解析
3. **Few-shot示例**：3个输入→意图映射→ 提供分类参考
4. **意图空间限定**：列出9种意图→ 避免模型自由发挥
5. **结构化输出**：要求`{"intent": "xxx"}`→ 程序可直接解析

**不同场景的Prompt策略**：
- 意图分类：简短+示例+JSON格式
- 信息提取：描述字段定义+示例输出
- 摘要生成：角色+目标+格式要求
- 心理评估：评估维度+评分标准+输出格式

---

### Q44：什么是知识库（Knowledge Base）？和数据库有什么区别？

**答：**

| 维度 | 知识库（Knowledge Base） | 数据库（Database） |
|------|------------------------|-------------------|
| 数据类型 | 非结构化文本（QA对、文档） | 结构化数据（表、行、列） |
| 查询方式 | 语义/关键词检索 | SQL精确查询 |
| 用途 | 给AI提供参考知识 | 存储业务数据 |
| 更新频率 | 低（偶尔更新文档） | 高（实时CRUD） |
| 一致性 | 最终一致即可 | 强一致性（ACID） |

**本项目两者的分工**：

| 场景 | 用知识库 | 用数据库 |
|------|---------|---------|
| "新加坡学费多少" | ✅ 检索FAQ | ❌ |
| "张三的请假状态" | ❌ | ✅ SQL查询 |
| "德国签证政策" | ✅ 检索文档 | ❌ |
| "录入新客户" | ❌ | ✅ INSERT |
| "公司新人入职流程" | ✅ 检索新人指南 | ❌ |

**本项目的知识库结构**：
```
knowledge_base/data/
├── 公司业务/       → 58条QA（项目详情、费用、流程）
├── 留学政策/       → 108条QA（签证、学费、PR）
├── 公司信息/       → 117条QA（公司介绍、新人指南、海外生活）
└── 用户研判规则/   → 1条示例数据
```

**知识库的加载和检索流程**：
```
启动时 → loader.py扫描目录加载所有.txt文件
      → splitter.py按500字切片（重叠50字）
      → vectorizer.py构建倒排索引
用户提问 → RAGEngine.search(用户输入) → 返回最相关的QA对
```

---

### Q45：项目没有外键约束，怎么处理脏数据的问题？

**答：**

**现状分析**：项目15张表中，仅 `event_registration.event_id` 声明了 `ForeignKey("event_lecture.id")`，其余所有关联字段（如 `student_id`、`employee_id`、`approver_id`、`owner_employee_id` 等）都是普通 `BigInteger` 列，没有数据库级外键约束。

---

**一、为什么不用外键？（设计权衡）**

| 维度 | 有外键约束 | 无外键约束（本项目） |
|------|-----------|-------------------|
| 数据库强一致 | ✅ 插入/删除自动校验 | ❌ 需应用层保证 |
| 性能 | 插入/删除需检查关联表，高并发下锁争抢 | 无额外检查，写入性能高 |
| 灵活性 | 必须按固定顺序插入（先父后子），删改受限 | 可任意顺序写入，运维灵活 |
| 跨库分表 | 外键不能跨库 | 天然支持微服务拆分 |
| 开发效率 | 需要维护约束关系，建表顺序严格 | 开发/测试更方便 |
| 软删除兼容 | 外键不认 `delete_flag`，物理删除才能级联 | 软删除+无外键，数据自然保留 |

**本项目选择无外键的核心原因**：
1. **软删除机制**：`delete_flag=1` 的记录不应被外键级联删除，业务需要保留关联数据
2. **SQLite/MySQL双适配**：外键行为在两种数据库中有差异，无外键降低迁移成本
3. **开发阶段灵活性**：快速迭代，不希望被外键约束阻碍数据插入顺序

---

**二、可能产生的脏数据类型**

| 脏数据类型 | 示例 | 风险等级 |
|-----------|------|---------|
| **悬空引用** | `student_admin_service.student_id=999`，但 `sys_user` 中无 id=999 的学生 | 🔴高 |
| **无效审批人** | `student_admin_service.approver_id=5`，但 id=5 的用户不是员工 | 🟡中 |
| **状态不一致** | 学生已软删除（`delete_flag=1`），但请假记录仍是"待审批" | 🟡中 |
| **数据孤岛** | `crm_lead.owner_employee_id` 指向已删除员工，客户无人跟进 | 🟡中 |
| **多态关联错误** | `notification.related_id` 指向不存在业务记录 | 🟢低 |

---

**三、本项目的脏数据处理策略（5层防护）**

#### 第1层：应用层写入校验（核心防线）

在 API 路由中，每次写入前**主动查询关联记录是否存在**：

```python
# student_routes.py - 提交请假
@router.post("/api/student/leave")
def create_leave(req: LeaveCreateRequest, db: Session = Depends(get_db),
                  current_user: SysUser = Depends(require_student)):
    # ✅ 校验1：关联的教务记录是否存在
    if req.related_academic_id:
        academic = db.query(StudentAcademic).filter(
            StudentAcademic.id == req.related_academic_id,
            StudentAcademic.delete_flag == 0
        ).first()
        if not academic:
            raise HTTPException(400, "关联的教务记录不存在")

    # ✅ 校验2：审批人必须是班主任角色
    head_teacher = db.query(SysUser).filter(
        SysUser.id == current_user.head_teacher_id,
        SysUser.delete_flag == 0
    ).first()
    if not head_teacher:
        raise HTTPException(400, "班主任信息异常，无法提交请假")
```

```python
# enterprise_routes.py - 新增意向客户
@router.post("/api/enterprise/lead")
def create_lead(req: LeadCreateRequest, db: Session = Depends(get_db),
                current_user: SysUser = Depends(require_employee)):
    # ✅ 校验：归属员工必须存在且在职
    employee = db.query(SysUser).filter(
        SysUser.id == req.owner_employee_id,
        SysUser.user_type == "EMPLOYEE",
        SysUser.delete_flag == 0
    ).first()
    if not employee:
        raise HTTPException(400, "归属员工不存在或已离职")
```

**关键原则**：所有 `_id` 字段在写入前，都必须查询关联记录是否存在 + `delete_flag==0`。

#### 第2层：依赖注入自动校验角色

通过 FastAPI 的 `Depends` 机制，在入口处自动拦截角色不匹配的请求：

```python
def require_student(current_user: SysUser = Depends(get_current_user)):
    if current_user.user_type != "STUDENT":
        raise HTTPException(403, "仅学生可访问")
    if current_user.delete_flag == 1:
        raise HTTPException(403, "账号已停用")
    return current_user

def require_employee(current_user: SysUser = Depends(get_current_user)):
    if current_user.user_type != "EMPLOYEE":
        raise HTTPException(403, "仅员工可访问")
    return current_user
```

→ 这保证了 `student_id` 一定是学生，`employee_id` 一定是员工，从源头减少角色错配的脏数据。

#### 第3层：软删除 + 级联状态处理

删除主记录时，主动处理关联子记录的状态：

```python
# 删除员工时的处理策略
def delete_employee(employee_id: int, db: Session):
    employee = db.query(SysUser).filter(SysUser.id == employee_id).first()
    employee.delete_flag = 1

    # ✅ 策略1：客户重新分配（推荐）
    leads = db.query(CrmLead).filter(CrmLead.owner_employee_id == employee_id,
                                       CrmLead.delete_flag == 0).all()
    for lead in leads:
        lead.status = "待分配"  # 标记为待重新分配，而非删除

    # ✅ 策略2：通知管理员
    # 创建系统通知，提醒管理员重新分配客户
```

```python
# 学生软删除时的处理
def delete_student(student_id: int, db: Session):
    student = db.query(SysUser).filter(SysUser.id == student_id).first()
    student.delete_flag = 1
    student.status = "已退学"

    # 子记录保留不动（请假/成绩/心理画像），通过 delete_flag 过滤查询
    # 如需隐藏：可批量设置子记录 delete_flag=1
```

#### 第4层：查询时安全过滤

所有查询统一加上 `delete_flag==0` 条件，即使存在悬空引用也不会展示脏数据：

```python
# 查询学生的请假记录
leaves = db.query(StudentAdminService).filter(
    StudentAdminService.student_id == student_id,
    StudentAdminService.delete_flag == 0  # ✅ 过滤已删除
).all()

# 关联查询：请假记录 + 学生姓名
leaves = db.query(StudentAdminService, SysUser.real_name)\
    .join(SysUser, StudentAdminService.student_id == SysUser.id, isouter=True)\
    .filter(StudentAdminService.delete_flag == 0,
            SysUser.delete_flag == 0).all()
# 使用 LEFT JOIN + 过滤，即使 student_id 悬空也不会报错，只是 real_name 为 NULL
```

#### 第5层：定期数据巡检（运维兜底）

编写数据一致性检查脚本，定期扫描脏数据：

```python
def check_data_integrity(db: Session):
    issues = []

    # 检查1：悬空 student_id
    orphan_services = db.query(StudentAdminService).filter(
        StudentAdminService.delete_flag == 0,
        ~StudentAdminService.student_id.in_(
            db.query(SysUser.id).filter(SysUser.delete_flag == 0)
        )
    ).all()
    issues.append(f"悬空 student_id 的行政服务: {len(orphan_services)}条")

    # 检查2：悬空 owner_employee_id
    orphan_leads = db.query(CrmLead).filter(
        CrmLead.delete_flag == 0,
        ~CrmLead.owner_employee_id.in_(
            db.query(SysUser.id).filter(SysUser.delete_flag == 0, SysUser.user_type == "EMPLOYEE")
        )
    ).all()
    issues.append(f"悬空 employee_id 的客户: {len(orphan_leads)}条")

    # 检查3：学生没有班主任
    students_no_teacher = db.query(SysUser).filter(
        SysUser.user_type == "STUDENT",
        SysUser.head_teacher_id == None,
        SysUser.delete_flag == 0
    ).all()
    issues.append(f"无班主任的学生: {len(students_no_teacher)}条")

    return issues
```

---

**四、如果答辩老师追问"为什么不加外键？"**

**推荐回答思路**：

> "这是一个有意识的设计权衡。外键约束的优势是数据库级强一致，但在我们的场景下有三个问题：
> 1. 软删除机制：`delete_flag` 是业务删除，不是物理删除，外键无法识别业务删除状态，会导致级联误删；
> 2. 双数据库适配：SQLite 默认不启用外键（需 `PRAGMA foreign_keys=ON`），MySQL 的外键行为也有差异，统一用应用层校验更可控；
> 3. 写入性能：批量导入测试数据时，外键约束要求严格的插入顺序，开发效率低。
>
> 替代方案是**应用层5层防护**：写入前主动校验关联存在性 → 依赖注入校验角色 → 软删除级联处理状态 → 查询统一过滤 → 定期巡检兜底。这种方案牺牲了数据库级的自动化保障，但换来了灵活性，在中小规模项目中是合理的权衡。生产环境如果对数据一致性要求极高，可以补充外键约束或改用数据库触发器。"

---

> 本文档基于项目源码全面分析生成，涵盖架构设计、AI技术、数据库、前端交互、安全工程、基础知识六大维度，共45道答辩问题及参考答案。
