"""
粤教服务 - 企业智能助手 API 路由
处理 CRM 客户管理 / 日报 / 员工查询等
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    LeadCreateRequest, LeadUpdateRequest,
    ReportCreateRequest, ScoreCreateRequest,
    EmployeeUpdateRequest, ProjectCreateRequest,
)
from crud import (
    UserCRUD, CrmCRUD, ReportCRUD, ScoreCRUD, EmployeeCRUD, DashboardCRUD,
    NotificationCRUD, ProjectCRUD,
)
from utils.auth import require_employee_or_admin
from model import SysUser

router = APIRouter(prefix="/api/enterprise", tags=["企业智能助手"])


# ==================== 意向客户管理 ====================

@router.post("/lead")
def create_lead(req: LeadCreateRequest, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """录入新意向客户"""
    data = req.model_dump(exclude_none=True)
    if not data.get("owner_employee_id"):
        data["owner_employee_id"] = current_user.id
    lead = CrmCRUD.create(db, **data)
    db.commit()
    return {"success": True, "lead_id": lead.id, "message": "客户录入成功"}


@router.get("/lead")
def list_leads(status: str = "", db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """查询意向客户列表"""
    leads = CrmCRUD.get_all(db, status)
    return {"leads": [
        {
            "id": l.id, "customer_name": l.customer_name,
            "contact_info": l.contact_info, "age": l.age,
            "education": l.education, "intended_country": l.intended_country,
            "intended_major": l.intended_major, "status": l.status,
            "score": l.score, "owner_employee_id": l.owner_employee_id,
            "next_follow_time": str(l.next_follow_time) if l.next_follow_time else None,
            "create_time": str(l.create_time),
        }
        for l in leads
    ]}


@router.put("/lead/{lead_id}")
def update_lead(lead_id: int, req: LeadUpdateRequest, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """更新意向客户信息"""
    lead = CrmCRUD.update(db, lead_id, **req.model_dump(exclude_none=True))
    if not lead:
        raise HTTPException(status_code=404, detail="客户不存在")
    db.commit()
    return {"success": True, "message": "客户信息更新成功"}


# ==================== 员工日报 ====================

@router.post("/report")
def submit_report(req: ReportCreateRequest, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """提交员工日报"""
    data = req.model_dump(exclude_none=True)
    if not data.get("report_date"):
        from datetime import date
        data["report_date"] = date.today()
    report = ReportCRUD.create(db, **data)
    db.commit()
    return {"success": True, "report_id": report.id, "message": "日报提交成功"}


@router.get("/report")
def list_reports(employee_id: int = 0, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """查询员工日报列表"""
    reports = ReportCRUD.get_all(db, employee_id)
    return {"reports": [
        {
            "id": r.id, "employee_id": r.employee_id,
            "report_date": str(r.report_date), "work_type": r.work_type,
            "content": r.content, "summary": r.summary,
            "report_status": r.report_status,
        }
        for r in reports
    ]}


# ==================== 学生成绩管理 ====================

@router.post("/score")
def add_score(req: ScoreCreateRequest, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """录入学生成绩"""
    score = ScoreCRUD.create(db, **req.model_dump(exclude_none=True))
    db.commit()
    return {"success": True, "score_id": score.id, "message": "成绩录入成功"}


@router.get("/score")
def list_scores(student_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """查询学生成绩"""
    scores = ScoreCRUD.get_by_student(db, student_id)
    return {"scores": [
        {
            "id": s.id, "course_name": s.course_name, "score": float(s.score),
            "total_score": float(s.total_score) if s.total_score else None,
            "exam_type": s.exam_type, "semester": s.semester,
            "exam_time": str(s.exam_time) if s.exam_time else None,
        }
        for s in scores
    ]}


# ==================== 学生成绩批量上传 ====================

@router.post("/score/batch")
async def batch_upload_scores(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """批量上传学生成绩（支持 Excel .xlsx / .csv）

    文件格式要求：
    - 必填列：学生ID(学号)、课程名称(科目)、成绩(分数)
    - 可选列：总分、及格线、考试类型、考试时间、学期、教师ID
    - 支持中文或英文字段名
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    from utils.file_parser import parse_score_file

    try:
        scores = parse_score_file(content, file.filename)
        if not scores:
            raise HTTPException(status_code=400, detail="未解析到有效数据，请检查文件格式")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = ScoreCRUD.batch_create(db, scores)
    db.commit()

    return {
        "success": True,
        "total": len(scores),
        "success_count": result["success_count"],
        "fail_count": result["fail_count"],
        "errors": result["errors"],
        "message": f"导入完成：成功 {result['success_count']} 条，失败 {result['fail_count']} 条",
    }


# ==================== 员工查询 ====================

@router.get("/employee")
def list_employees(db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """查询员工列表"""
    employees = EmployeeCRUD.get_all(db)
    return {"employees": [
        {
            "id": e.id, "real_name": e.real_name,
            "employee_role": e.employee_role, "department": e.department,
            "contact_info": e.contact_info, "email": e.email,
        }
        for e in employees
    ]}


@router.put("/employee/{employee_id}")
def update_employee(employee_id: int, req: EmployeeUpdateRequest, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """修改员工通讯录信息（仅员工/管理员可操作）"""
    employee = EmployeeCRUD.update(db, employee_id, **req.model_dump(exclude_none=True))
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    db.commit()
    return {"success": True, "message": "员工信息已更新"}


# ==================== 课程项目管理 ====================

@router.post("/project")
def create_project(req: ProjectCreateRequest, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """添加课程项目（员工/管理员可操作）"""
    project = ProjectCRUD.create(db, **req.model_dump(exclude_none=True))
    db.commit()
    return {"success": True, "project_id": project.id, "message": "项目添加成功"}


@router.delete("/project/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """删除课程项目（仅管理员可操作，软删除）"""
    if current_user.user_type != "ADMIN":
        raise HTTPException(status_code=403, detail="仅管理员可删除项目")
    project = ProjectCRUD.delete(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    db.commit()
    return {"success": True, "message": "项目已删除"}


# ==================== 仪表盘 ====================

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """企业助手仪表盘"""
    return DashboardCRUD.get_stats(db)


# ==================== 审批管理（班主任） ====================

@router.get("/approvals/pending")
def list_pending_approvals(db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """班主任查看名下学生的待审批列表"""
    if current_user.user_type != "ADMIN" and current_user.employee_role != "班主任":
        raise HTTPException(status_code=403, detail="仅班主任可查看待审批列表")

    from agents.student.approval_flow import ApprovalFlow
    flow = ApprovalFlow()
    pending = flow.get_pending_by_teacher(db, current_user.id)
    return {"pending": pending, "count": len(pending)}


class ApproveRequest:
    """审批请求体"""
    def __init__(self, approved: bool = True, reject_reason: str = None):
        self.approved = approved
        self.reject_reason = reject_reason


@router.post("/approvals/{approval_id}/approve")
def approve_request(approval_id: int, message: dict, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """班主任审批请假申请（同意/驳回）"""
    if current_user.user_type != "ADMIN" and current_user.employee_role != "班主任":
        raise HTTPException(status_code=403, detail="仅班主任可审批")

    from model import StudentAdminService, SysUser
    from agents.student.approval_flow import ApprovalFlow

    # 校验该申请属于当前班主任名下的学生
    record = db.query(StudentAdminService).filter(
        StudentAdminService.id == approval_id,
        StudentAdminService.delete_flag == 0,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="申请不存在")

    student = db.query(SysUser).filter(
        SysUser.id == record.student_id,
        SysUser.delete_flag == 0,
    ).first()
    if not student or student.head_teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="该申请不属于你名下的学生，无权审批")

    flow = ApprovalFlow()
    approved = message.get("approved", True)
    reject_reason = message.get("reject_reason") if not approved else None

    result = flow.approve(db, approval_id, current_user.id, approved, reject_reason)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # 创建通知给对应学生
    if approved:
        notif_title = "请假申请已通过"
        notif_content = f"您的{record.leave_type or '请假'}申请（{str(record.start_time)[:16] if record.start_time else ''} ~ {str(record.end_time)[:16] if record.end_time else ''}）已由{current_user.real_name}审批通过。"
        notif_type = "leave_approved"
    else:
        notif_title = "请假申请已驳回"
        notif_content = f"您的{record.leave_type or '请假'}申请已被驳回。原因：{reject_reason or '无'}"
        notif_type = "leave_rejected"

    NotificationCRUD.create(
        db,
        recipient_id=record.student_id,
        title=notif_title,
        content=notif_content,
        notification_type=notif_type,
        related_id=approval_id,
    )

    db.commit()

    return {
        "success": True,
        "message": result["message"],
        "student_name": student.real_name,
        "student_contact": student.contact_info,
        "student_email": student.email,
        "leave_type": record.leave_type,
        "start_time": str(record.start_time) if record.start_time else None,
        "end_time": str(record.end_time) if record.end_time else None,
        "teacher_name": current_user.real_name,
        "teacher_email": current_user.email,
    }


# ==================== 组织架构 ====================

@router.get("/org-chart")
def org_chart(db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """查询公司组织架构树"""
    from crud import OrgCRUD
    tree = OrgCRUD.get_tree(db)
    return {"org_tree": tree}


@router.get("/org-chart/department")
def org_department(dept_name: str = "", db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """按部门名称查员工列表"""
    from crud import OrgCRUD
    if dept_name:
        members = OrgCRUD.get_dept_members(db, dept_name)
        return {
            "department": dept_name,
            "members": [
                {"id": m.id, "real_name": m.real_name, "role": m.employee_role,
                 "contact_info": m.contact_info, "email": m.email}
                for m in members
            ]
        }
    depts = OrgCRUD.get_all(db)
    return {"departments": [
        {"id": d.id, "name": d.dept_name, "desc": d.dept_desc,
         "level": d.dept_level, "parent_id": d.parent_id,
         "contact_phone": d.contact_phone, "contact_email": d.contact_email}
        for d in depts
    ]}


# ==================== 企业助手对话接口 ====================

@router.post("/chat")
def enterprise_chat(message: dict, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """企业助手对话接口（支持NL2SQL/日报/CRM等）"""
    from agents.enterprise.agent import EnterpriseAgent
    agent = EnterpriseAgent()
    text = message.get("message", "")
    result = agent.route_intent(text, db=db)
    return result


@router.post("/nl2sql")
def nl2sql_query(message: dict, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """自然语言转SQL查询"""
    from agents.enterprise.agent import EnterpriseAgent
    agent = EnterpriseAgent()
    text = message.get("message", "")
    result = agent.query_database(text, db)
    return result


@router.post("/nl2sql/update")
def nl2sql_update(message: dict, db: Session = Depends(get_db), current_user: SysUser = Depends(require_employee_or_admin)):
    """自然语言转SQL更新（安全白名单：仅支持crm_lead/feedback/admin_service/academic的特定列）"""
    from agents.enterprise.agent import EnterpriseAgent
    agent = EnterpriseAgent()
    text = message.get("message", "")
    result = agent.nl2sql.update(db, text)
    return result


@router.post("/voice-report")
def voice_to_report(message: dict, current_user: SysUser = Depends(require_employee_or_admin)):
    """口述文本 → 结构化日报"""
    from agents.enterprise.agent import EnterpriseAgent
    agent = EnterpriseAgent()
    text = message.get("message", "")
    report = agent.voice_to_report(text)
    return {"success": True, "report": report}
