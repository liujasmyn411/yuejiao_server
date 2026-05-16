"""
定时任务调度器
DDL提醒 / 周报自动生成 / 主动推送
"""
import logging
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal

logger = logging.getLogger("yuejiao.scheduler")

scheduler = BackgroundScheduler()


def _ddl_reminder():
    """DDL提醒：检查未来N天内的待完成教务事项，推送通知"""
    from model import StudentAcademic, Notification

    db = SessionLocal()
    try:
        now = datetime.now()
        academics = db.query(StudentAcademic).filter(
            StudentAcademic.delete_flag == 0,
            StudentAcademic.ddl_status == "未完成",
            StudentAcademic.remind_enabled == 1,
        ).all()

        notified = 0
        for a in academics:
            if not a.deadline or not a.remind_days_before:
                continue

            days_left = (a.deadline - now).days
            remind_days = [int(d.strip()) for d in a.remind_days_before.split(",") if d.strip().isdigit()]

            for rd in remind_days:
                if days_left == rd:
                    # 检查今天是否已经提醒过
                    if a.last_remind_time and a.last_remind_time.date() == now.date():
                        continue

                    notif = Notification(
                        recipient_id=a.student_id,
                        title=f"DDL提醒：{a.title}",
                        content=f"{a.course_name}的{a.academic_type}「{a.title}」将在{rd}天后截止（{str(a.deadline)[:16]}），请尽快完成。",
                        notification_type="ddl_reminder",
                        related_id=a.id,
                    )
                    db.add(notif)
                    a.last_remind_time = now
                    notified += 1
                    break

        if notified:
            db.commit()
            logger.info(f"DDL提醒：已发送 {notified} 条通知")
    except Exception as e:
        logger.error(f"DDL提醒任务异常: {e}")
        db.rollback()
    finally:
        db.close()


def _auto_weekly_reports():
    """自动生成周报（每周一执行）"""
    from reports.report_generator import ReportGenerator

    db = SessionLocal()
    try:
        gen = ReportGenerator()
        psych_report = gen.generate(db, "psych_weekly")
        complaint_report = gen.generate(db, "complaint_weekly")

        # 检查是否有高危学生，有则给班主任发通知
        high_risk = psych_report.get("data", {}).get("high_risk_students", [])
        if high_risk:
            from model import Notification, SysUser
            teachers = db.query(SysUser).filter(
                SysUser.user_type == "EMPLOYEE",
                SysUser.employee_role == "班主任",
                SysUser.delete_flag == 0,
            ).all()
            for t in teachers:
                notif = Notification(
                    recipient_id=t.id,
                    title="心理健康周报提醒",
                    content=f"本周有{len(high_risk)}名高危心理风险学生，请登录系统查看心理健康周报。",
                    notification_type="weekly_report",
                )
                db.add(notif)
            db.commit()

        logger.info(f"周报自动生成完成: psych={psych_report.get('data',{}).get('本周预警数',0)}条预警, complaint={complaint_report.get('data',{}).get('总工单数',0)}条工单")
    except Exception as e:
        logger.error(f"周报自动生成异常: {e}")
        db.rollback()
    finally:
        db.close()


def _pending_followup_reminder():
    """主动推送：检查待处理的投诉/待审批的请假，提醒相关负责人"""
    from model import StudentFeedbackTicket, StudentAdminService, Notification, SysUser

    db = SessionLocal()
    try:
        # 待处理投诉 > 3天 → 提醒班主任
        cutoff = datetime.now() - timedelta(days=3)
        stale_tickets = db.query(StudentFeedbackTicket).filter(
            StudentFeedbackTicket.status == "待处理",
            StudentFeedbackTicket.delete_flag == 0,
            StudentFeedbackTicket.create_time <= cutoff,
        ).all()

        if stale_tickets:
            teachers = db.query(SysUser).filter(
                SysUser.user_type == "EMPLOYEE",
                SysUser.employee_role == "班主任",
                SysUser.delete_flag == 0,
            ).all()
            for t in teachers:
                notif = Notification(
                    recipient_id=t.id,
                    title="待处理投诉提醒",
                    content=f"有{len(stale_tickets)}条投诉工单超过3天未处理，请及时跟进。",
                    notification_type="followup_reminder",
                )
                db.add(notif)
            db.commit()
            logger.info(f"待处理投诉提醒：{len(stale_tickets)} 条超时工单")

        # 待审批请假 > 2天 → 提醒班主任
        cutoff_leave = datetime.now() - timedelta(days=2)
        stale_leaves = db.query(StudentAdminService).filter(
            StudentAdminService.status == "待审批",
            StudentAdminService.delete_flag == 0,
            StudentAdminService.create_time <= cutoff_leave,
        ).all()

        if stale_leaves:
            teacher_ids = set()
            for leave in stale_leaves:
                student = db.query(SysUser).filter(
                    SysUser.id == leave.student_id,
                    SysUser.delete_flag == 0,
                ).first()
                if student and student.head_teacher_id:
                    teacher_ids.add(student.head_teacher_id)

            for tid in teacher_ids:
                count = sum(1 for l in stale_leaves
                           if db.query(SysUser).filter(SysUser.id == l.student_id, SysUser.head_teacher_id == tid).first())
                notif = Notification(
                    recipient_id=tid,
                    title="待审批请假提醒",
                    content=f"您有{count}条请假申请超过2天未审批，请及时处理。",
                    notification_type="followup_reminder",
                )
                db.add(notif)
            db.commit()
            logger.info(f"待审批请假提醒：{len(stale_leaves)} 条超时申请")
    except Exception as e:
        logger.error(f"待处理跟进提醒异常: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """启动定时任务调度器"""
    # 每天早上9点检查DDL提醒
    scheduler.add_job(_ddl_reminder, "cron", hour=9, minute=7, id="ddl_reminder")

    # 每周一早上9点自动生成周报
    scheduler.add_job(_auto_weekly_reports, "cron", day_of_week="mon", hour=9, minute=17, id="weekly_reports")

    # 每天下午3点检查待处理超时工单和待审批请假
    scheduler.add_job(_pending_followup_reminder, "cron", hour=15, minute=7, id="followup_reminder")

    scheduler.start()
    logger.info("定时任务调度器已启动 (DDL提醒/周报/跟进提醒)")


def stop_scheduler():
    """停止定时任务调度器"""
    scheduler.shutdown()
    logger.info("定时任务调度器已停止")
