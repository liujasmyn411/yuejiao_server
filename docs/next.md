# 修改规划

---

## 1. 学生反馈建议后，管理员通知中心收不到反馈通知

**问题**：学生提交反馈（`POST /api/student/feedback`）后，只创建了工单，没有给管理员/员工发送通知。目前通知仅在反馈**被处理**时才创建。

**修改文件**：

### 1.1 `api/student_routes.py` — `create_feedback` 函数（约第113行）

在 `db.commit()` 之前，新增逻辑：
- 查询所有 `user_type = 'ADMIN'` 的用户，以及所有 `employee_role = '班主任'` 的 EMPLOYEE 用户
- 为每个管理员/班主任调用 `NotificationCRUD.create()` 创建通知
- 通知类型：`new_feedback`
- 通知标题：`"新反馈工单"`
- 通知内容：包含学生姓名、反馈类型、内容摘要、紧急程度
- 同时也给提交反馈的学生本人发一条确认通知（告知已收到反馈）

### 1.2 前端 `static/js/pages/notifications.js`

确认通知列表能正确渲染 `new_feedback` 类型的通知（通常已有通用渲染，检查即可）。

### 1.3 前端 `static/js/components/topbar.js`

确认未读通知数徽章能正常拉取（已通过 `/api/student/notification/unread-count` 实现，无需改动）。

---

## 2. 管理员可以修改学生的留学进度，修改员工通讯录

### 2.1 修改留学进度

#### 2.1.1 `crud/student_crud.py` — `StudyAbroadCRUD` 类

新增方法：
- `update(db, progress_id, **kwargs)` — 更新单条留学进度记录（stage, stage_status, stage_detail, handler_name, estimated_complete_date, actual_complete_date, is_current 等）
- 如果设置 `is_current=1`，需先将该学生其他记录的 `is_current` 置 0

#### 2.1.2 `schemas/schemas.py` — 新增 Schema

```python
class StudyAbroadUpdateRequest(BaseSchema):
    target_country: str | None = None
    target_school: str | None = None
    target_major: str | None = None
    degree_level: str | None = None
    stage: str | None = None
    stage_order: int | None = None
    stage_status: str | None = None
    stage_detail: str | None = None
    handler_name: str | None = None
    handler_contact: str | None = None
    estimated_complete_date: str | None = None
    actual_complete_date: str | None = None
    is_current: int | None = None
```

#### 2.1.3 `api/student_routes.py` — 新增路由

```python
@router.put("/api/student/study-abroad/{progress_id}")
def update_study_abroad_progress(progress_id: int, req: StudyAbroadUpdateRequest, ...):
    """管理员修改学生留学进度（仅 ADMIN/EMPLOYEE 可操作）"""
```

权限：`require_employee_or_admin`

#### 2.1.4 前端 `static/js/pages/studyAbroad.js`

在留学进度页面增加"编辑"按钮，点击弹出模态框修改各阶段信息。

### 2.2 修改员工通讯录

#### 2.2.1 `crud/enterprise_crud.py` — `EmployeeCRUD` 类

新增方法：
- `update(db, employee_id, **kwargs)` — 更新员工信息（contact_info, email, department, employee_role, status 等）

#### 2.2.2 `schemas/schemas.py` — 新增 Schema

```python
class EmployeeUpdateRequest(BaseSchema):
    real_name: str | None = None
    department: str | None = None
    employee_role: str | None = None
    contact_info: str | None = None
    email: str | None = None
    status: str | None = None
```

#### 2.2.3 `api/enterprise_routes.py` — 新增路由

```python
@router.put("/employee/{employee_id}")
def update_employee(employee_id: int, req: EmployeeUpdateRequest, ...):
    """修改员工通讯录信息（仅 ADMIN 可操作）"""
```

权限：仅 ADMIN（或 ADMIN + 员工本人）

#### 2.2.4 前端 `static/js/pages/employees.js`

在员工列表每行增加"编辑"按钮，点击弹出模态框修改通讯信息。

---

## 3. 课程项目增加添加和删除按钮

### 3.1 `crud/customer_crud.py` — `ProjectCRUD` 类

新增方法：
- `create(db, **kwargs)` — 创建新课程项目
- `delete(db, project_id)` — 软删除课程项目（设置 `delete_flag=1`）

### 3.2 `schemas/schemas.py` — 新增 Schema

```python
class ProjectCreateRequest(BaseSchema):
    project_name: str
    category: str = ""
    country: str = ""
    tuition_fee: str = ""
    duration: str = ""
    description: str = ""
    target_audience: str = ""
    application_require: str = ""
    is_recommended: int = 0
    age_min: int | None = None
    age_max: int | None = None
```

### 3.3 `api/enterprise_routes.py`（或 `api/customer_routes.py`）— 新增路由

放在 `enterprise_routes.py` 中（因为添加/删除是管理操作，需要员工/管理员权限）：

```python
@router.post("/project")
def create_project(req: ProjectCreateRequest, ...):
    """添加课程项目（仅 ADMIN/EMPLOYEE）"""

@router.delete("/project/{project_id}")
def delete_project(project_id: int, ...):
    """删除课程项目（仅 ADMIN/EMPLOYEE，软删除）"""
```

> **说明**：如果希望前端 `/projects` 页面也能管理项目，建议将 POST/DELETE 放在 `enterprise_routes.py`（需要权限），GET 保持在 `customer_routes.py`（无需权限，供外部访客浏览）。

### 3.4 前端 `static/js/pages/projects.js`

在项目列表每行增加"删除"按钮（红色，需二次确认），页面顶部增加"添加项目"按钮，点击弹出表单模态框。

---

## 4. 文件解析改为客户意向研判

**需求**：上传文件后，自动根据 `knowledge_base/data/用户研判规则/` 判定是否为意向客户，返回研判结果。如果是意向客户，自动写入 `crm_lead`。

**修改文件**：

### 4.1 `utils/file_parser.py` — 新增公共意向研判函数（需求4 & 需求7 共用）

新增函数 `assess_lead_intention(profile: dict) -> dict`，此函数为需求4（文件解析）和需求7（对话浮窗）的统一研判入口：

- 输入：从文件解析提取的客户画像字段（age, education, intended_country 等）
- 逻辑（参考 `knowledge_base/data/用户研判规则/用户画像研判规则.md`）：

  **新加坡项目判定**：
  - 年龄 14-19 岁 + 初中/高中/中专学历 → 匹配新加坡国际本硕升学计划
  - 年龄 ≥17 岁 + 职高/中专学历 → 匹配酒店/航空大专就业班
  - 评分维度：年龄匹配（30分），学历匹配（25分），家庭经济（10分），语言能力（10分），留学意愿（15分），其他加分（10分）

  **德国项目判定**：
  - 年龄 18-35 岁 + 高中及以上学历 → 匹配中德精英人才共建计划
  - 评分维度：年龄匹配（25分），学历匹配（20分），职业技能（15分），语言能力（15分），家庭经济（10分），留学意愿（15分）

  - 总分 ≥50 分 → 判定为意向客户
  - 返回：`{is_intended: bool, score: int, matched_program: str, reasons: list, lead_data: dict}`

### 4.2 `utils/file_parser.py` — 改进 `extract_profile_from_text`

增强字段提取：增加对家庭经济状况、语言水平、背景信息等字段的提取模式。

### 4.3 `api/customer_routes.py` — 改造 `parse_customer_file` 接口（约第225行）

改造流程：
1. 解析文件（保持不变）
2. 提取画像字段（增强版）
3. **调用 `assess_lead_intention()`** 进行意向研判
4. **如果是意向客户**：
   - 自动调用 `CrmCRUD.create()` 写入 `crm_lead` 表
   - `source_channel` 设为 `"文件解析"`
   - `owner_employee_id` 可设为默认管理员或从请求参数传入
   - `status` 设为 `"新增意向"`
5. 返回结果增加字段：

```json
{
  "success": true,
  "filename": "...",
  "text": "...",
  "extracted_profile": {...},
  "assessment": {
    "is_intended": true,
    "score": 75,
    "matched_program": "新加坡国际本硕升学计划",
    "reasons": ["年龄匹配: 16岁", "学历匹配: 高中", "意向国家匹配: 新加坡"],
    "lead_created": true,
    "lead_id": 123
  }
}
```

### 4.4 `api/customer_routes.py` — 新增依赖注入

接口需要注入 `db: Session`（当前 `parse_customer_file` 没有 db 参数，需要加上）。

### 4.5 前端 `static/js/pages/parseFile.js`

更新文件上传成功后的展示，显示研判结果卡片（匹配项目、评分、原因、是否已自动录入CRM）。

---

## 5. 学生成绩添加文件批量上传

### 5.1 `schemas/schemas.py` — 新增 Schema

```python
class ScoreBatchItem(BaseSchema):
    student_id: int
    course_name: str
    score: float
    total_score: float | None = None
    pass_score: float | None = None
    exam_type: str = ""
    exam_time: str | None = None
    semester: str = ""
    teacher_id: int | None = None
```

### 5.2 `crud/enterprise_crud.py` — `ScoreCRUD` 类

新增方法：
- `batch_create(db, scores: list[dict]) -> dict` — 批量创建成绩，返回成功/失败统计
  - 逐条校验 student_id 是否存在
  - 跳过重复记录（相同学期+相同课程+相同考试类型）
  - 返回 `{success_count, fail_count, errors: [...]}`

### 5.3 `api/enterprise_routes.py` — 新增路由

```python
@router.post("/score/batch")
async def batch_upload_scores(file: UploadFile = File(...), db=Depends(get_db), current_user=Depends(require_employee_or_admin)):
    """批量上传学生成绩（支持 Excel .xlsx / .csv）"""
```

处理流程：
1. 读取上传文件（Excel 或 CSV）
2. 解析表头映射到 ScoreBatchItem 字段
3. 逐行校验（必填字段：student_id, course_name, score）
4. 调用 `ScoreCRUD.batch_create()`
5. 返回上传结果（成功数、失败数、失败行详情）

### 5.4 文件解析工具增强 `utils/file_parser.py`

新增 `parse_score_file(file_bytes, filename) -> list[dict]`：
- 支持 Excel 和 CSV
- 自动识别表头（支持中英文列名映射）
- 返回结构化的成绩列表

### 5.5 前端 `static/js/pages/scores.js`

在成绩管理页面增加"批量导入"按钮，点击弹出文件上传模态框，上传后显示导入结果。

---

## 6. 组织架构里的员工如果辞职怎么办（暂缓实现）

> **决定**：此需求暂时不实现，后续再议。

### 6.1 `crud/enterprise_crud.py` — `EmployeeCRUD` 类

新增方法：
- `resign(db, employee_id, reason="", reassign_employee_id=None) -> dict`
  - 将员工 `status` 设为 `"离职"`
  - 将该员工的 `delete_flag` 设为 `1`（软删除）
  - **CRM 客户交接**：将该员工名下所有 `crm_lead` 的 `owner_employee_id` 重新分配给 `reassign_employee_id`（或默认管理员）
  - **审批权交接**：如果该员工是班主任（`employee_role='班主任'`），将其名下学生的 `head_teacher_id` 重新分配
  - 记录操作日志（可选）
  - 返回交接统计：`{reassigned_leads: N, reassigned_students: M}`

### 6.2 `schemas/schemas.py` — 新增 Schema

```python
class EmployeeResignRequest(BaseSchema):
    reason: str = ""
    reassign_employee_id: int | None = None  # 接手员工ID
```

### 6.3 `api/enterprise_routes.py` — 新增路由

```python
@router.put("/employee/{employee_id}/resign")
def resign_employee(employee_id: int, req: EmployeeResignRequest, ...):
    """员工离职处理（仅 ADMIN 可操作）"""
```

权限：仅 ADMIN

### 6.4 前端 `static/js/pages/employees.js`

在员工列表每行增加"离职"按钮（需二次确认 + 选择交接人），点击后调用离职接口。

### 6.5 离职后的影响范围（需在实现时确认）

- `crm_lead` 表：`owner_employee_id` 需交接
- `sys_user` 表：学生 `head_teacher_id` 需交接（若辞职员工是班主任）
- `student_admin_service` 表：`approver_id` 的历史记录保留不动
- `notification` 表：历史通知保留不动
- 员工本人不能再登录系统（`delete_flag=1` 后 `get_by_username` 查不到）

---

## 7. AI 对话浮窗中，管理员/员工用自然语言研判意向客户

**需求**：在 AI 对话浮窗中（`/api/chat` 统一入口或企业助手对话），管理员/员工用自然语言描述用户信息，系统根据研判规则判定是否为意向客户，如果是则自动写入 `crm_lead`。

**现状**：EnterpriseAgent 已有 `lead_profile` 意图，会调用 `_handle_lead_profile` 进行画像分析和自动录入。但需要增强使其更完整地使用 `knowledge_base/data/用户研判规则/` 中的规则。

**修改文件**：

### 7.1 `agents/enterprise/prompts.py` — 增强 `LEAD_PROFILE_PROMPT`

当前 `LEAD_PROFILE_PROMPT` 需要增强：
- 将 `knowledge_base/data/用户研判规则/用户画像研判规则.md` 中的完整规则嵌入提示词
- 明确新加坡项目（年龄 14-19）和德国项目（年龄 18-35）的判定条件
- 增加评分细则：年龄、学历、家庭经济、语言能力、留学意愿等维度的权重
- 要求 LLM 返回结构化的研判结果：`{is_intended, score, program, reasons, extracted_fields}`

### 7.2 `agents/enterprise/agent.py` — 增强 `_handle_lead_profile` 方法

当前流程：
1. LLM 从自然语言中提取结构化字段 ✓
2. 调用 `_evaluate_profile()` 做简单评分（新加坡 age 14-19，德国 age 18-35）
3. 如果匹配则自动创建 CRM lead

需要增强：
- 将 `_evaluate_profile()` 的评分逻辑改为调用公共函数 `assess_lead_intention()`（`utils/file_parser.py`），与需求4 共用同一套研判逻辑
- 评分 ≥50 分才判定为意向客户，自动录入 CRM
- 未达到阈值时，返回"暂不判定为意向客户"及原因分析
- 支持在对话中补充信息后重新研判（多轮对话）

### 7.3 `agents/enterprise/agent.py` — 新增意图关键词

在 `_quick_route` 中增加 `lead_profile` 意图的快速触发词：
- `"研判"`, `"意向"`, `"画像"`, `"分析一下"`, `"帮我看下"`, `"这个客户"`, `"意向客户"`, `"是不是意向"`

### 7.4 `api/chat_routes.py` — 确认统一入口可用

当前 `/api/chat` 已正确路由 `enterprise` 意图到 `EnterpriseAgent`。`lead_profile` 意图在 `INTENT_DESCRIPTIONS` 中已定义。确认以下流程畅通：
1. 用户在浮窗输入自然语言描述 → `/api/chat`
2. LLM 分类为 `enterprise` → 路由到 `EnterpriseAgent.route_intent()`
3. `EnterpriseAgent` 识别 `lead_profile` 意图 → 调用 `_handle_lead_profile()`
4. 返回研判结果 + 是否已录入 CRM

无需修改 `chat_routes.py`，但需验证 LLM 意图分类能正确将"用户画像描述"分类为 `enterprise`。

### 7.5 `api/chat_routes.py` — 可选增强：增加 lead_profile 关键词

在 `ENTERPRISE_KW` 中增加关键词：
```python
'研判', '是不是意向', '能不能成', '有戏吗', '潜力', '评估一下'
```

### 7.6 前端 `static/js/components/chat.js`

确认聊天浮窗能正确展示研判结果（包括评分、匹配项目、是否已录入CRM等结构化信息）。如果 result 中包含 `assessment` 字段，使用卡片样式突出显示。

---

## 涉及文件汇总

| 文件 | 需求 |
|------|------|
| `api/student_routes.py` | 需求1（反馈通知）, 需求2.1（留学进度修改） |
| `api/enterprise_routes.py` | 需求2.2（员工修改）, 需求3（项目增删）, 需求5（成绩批量） |
| `api/customer_routes.py` | 需求3（项目GET不变）, 需求4（文件解析改造） |
| `api/chat_routes.py` | 需求7（关键词增强, 可选） |
| `crud/student_crud.py` | 需求2.1（StudyAbroadCRUD.update） |
| `crud/enterprise_crud.py` | 需求2.2（EmployeeCRUD.update）, 需求5（ScoreCRUD.batch_create） |
| `crud/customer_crud.py` | 需求3（ProjectCRUD.create/delete） |
| `schemas/schemas.py` | 需求2-5（新增多个 Request Schema） |
| `utils/file_parser.py` | 需求4（assess_lead_intention）, 需求5（parse_score_file） |
| `agents/enterprise/prompts.py` | 需求7（LEAD_PROFILE_PROMPT 增强） |
| `agents/enterprise/agent.py` | 需求7（_handle_lead_profile 增强, _quick_route 增强） |
| `agents/customer_service/agent.py`| 需求4（可选，客服agent也可调用研判） |
| 前端 `employees.js` | 需求2.2 |
| 前端 `studyAbroad.js` | 需求2.1 |
| 前端 `projects.js` | 需求3 |
| 前端 `parseFile.js` | 需求4 |
| 前端 `scores.js` | 需求5 |
| 前端 `chat.js` | 需求7 |

---

## 已确认事项

1. **需求4 和 需求7 研判规则统一** → 提取公共的 `assess_lead_intention()` 函数（放在 `utils/file_parser.py`），文件解析和对话浮窗共用同一套逻辑。

2. **需求6 员工离职** → 暂时不实现，后续再议。

3. **需求3 课程项目权限** → ADMIN 可删除，EMPLOYEE 可添加。

4. **需求5 成绩批量上传** → 提供 CSV/Excel 模板下载。

5. **需求4 非意向客户展示** → 前端展示"非意向客户"及原因分析，让用户了解为何未自动录入。
