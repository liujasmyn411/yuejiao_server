"""
学生助手 - 审批流程引擎
请假/考务申请的提交、追踪、审批闭环
"""
from datetime import datetime
from typing import Optional
from utils.llm_client import get_llm_client


class ApprovalFlow:
    """审批流程管理：请假 → 审批 → 通知 闭环"""

    def __init__(self):
        self.llm = get_llm_client()

    def submit(self, db, student_id: int, service_type: str,
               leave_type: str = None, start_time: datetime = None,
               end_time: datetime = None, reason: str = None) -> dict:
        """提交审批申请"""
        from model import StudentAdminService

        record = StudentAdminService(
            student_id=student_id,
            service_type=service_type,
            leave_type=leave_type,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
            status="待审批",
        )
        db.add(record)
        db.flush()
        return {
            "status": "submitted",
            "id": record.id,
            "message": f"{service_type}申请已提交，请等待班主任审批",
        }

    def check_status(self, db, request_id: int) -> dict:
        """查询审批状态"""
        from model import StudentAdminService

        record = db.query(StudentAdminService).filter(
            StudentAdminService.id == request_id,
            StudentAdminService.delete_flag == 0,
        ).first()

        if not record:
            return {"status": "not_found", "id": request_id, "message": "申请不存在"}

        return {
            "status": record.status,
            "id": record.id,
            "service_type": record.service_type,
            "leave_type": record.leave_type,
            "start_time": str(record.start_time) if record.start_time else None,
            "end_time": str(record.end_time) if record.end_time else None,
            "reason": record.reason,
            "reject_reason": record.reject_reason,
            "created_at": str(record.create_time),
        }

    def approve(self, db, request_id: int, approver_id: int,
                approved: bool = True, reject_reason: str = None) -> dict:
        """审批（同意或驳回）"""
        from model import StudentAdminService

        record = db.query(StudentAdminService).filter(
            StudentAdminService.id == request_id,
            StudentAdminService.delete_flag == 0,
        ).first()

        if not record:
            return {"success": False, "message": "申请不存在"}

        if record.status != "待审批":
            return {"success": False, "message": f"申请状态为{record.status}，无法重复审批"}

        record.approver_id = approver_id
        if approved:
            record.status = "已通过"
            record.notify_status = 1
            return {"success": True, "message": "申请已通过"}
        else:
            record.status = "已驳回"
            record.reject_reason = reject_reason
            record.notify_status = 1
            return {"success": True, "message": f"申请已驳回: {reject_reason or ''}"}

    def get_pending_approvals(self, db, approver_id: int = None) -> list:
        """获取待审批列表"""
        from model import StudentAdminService

        q = db.query(StudentAdminService).filter(
            StudentAdminService.status == "待审批",
            StudentAdminService.delete_flag == 0,
        )
        return q.order_by(StudentAdminService.create_time.desc()).all()

    def get_pending_by_teacher(self, db, teacher_id: int) -> list[dict]:
        """班主任查看自己名下学生的待审批列表"""
        from model import StudentAdminService, SysUser

        students = db.query(SysUser).filter(
            SysUser.head_teacher_id == teacher_id,
            SysUser.user_type == "STUDENT",
            SysUser.delete_flag == 0,
        ).all()
        student_ids = [s.id for s in students]

        if not student_ids:
            return []

        records = (
            db.query(StudentAdminService)
            .filter(
                StudentAdminService.student_id.in_(student_ids),
                StudentAdminService.status == "待审批",
                StudentAdminService.delete_flag == 0,
            )
            .order_by(StudentAdminService.create_time.desc())
            .all()
        )

        student_map = {s.id: s for s in students}
        return [
            {
                "id": r.id,
                "student_id": r.student_id,
                "student_name": student_map.get(r.student_id, SysUser()).real_name,
                "service_type": r.service_type,
                "leave_type": r.leave_type,
                "start_time": str(r.start_time) if r.start_time else None,
                "end_time": str(r.end_time) if r.end_time else None,
                "reason": r.reason,
                "status": r.status,
                "create_time": str(r.create_time),
            }
            for r in records
        ]

    def extract_leave_info(self, user_input: str) -> dict:
        """从自然语言中提取请假信息"""
        info = self.llm.extract_info(
            user_input,
            ["请假类型", "开始时间", "结束时间", "请假原因"]
        )
        leave_type = info.get("请假类型", "")
        if not leave_type:
            if "病" in user_input:
                leave_type = "病假"
            elif "事" in user_input or "私" in user_input:
                leave_type = "事假"
            else:
                leave_type = "事假"

        return {
            "leave_type": leave_type,
            "start_time": info.get("开始时间"),
            "end_time": info.get("结束时间"),
            "reason": info.get("请假原因", user_input),
        }
