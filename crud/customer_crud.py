"""
粤教服务 - 客服智能助手 CRUD 数据访问层
封装活动讲座、课程项目的数据库操作
"""

from sqlalchemy.orm import Session

from model import EventLecture, EventRegistration, CourseProject


class EventCRUD:
    """活动讲座数据访问对象"""

    @staticmethod
    def create(db: Session, **kwargs):
        """创建活动"""
        event = EventLecture(**kwargs)
        db.add(event)
        return event

    @staticmethod
    def get_by_id(db: Session, event_id: int):
        """根据ID查询活动"""
        return db.query(EventLecture).filter(
            EventLecture.id == event_id,
            EventLecture.delete_flag == 0
        ).first()

    @staticmethod
    def get_all(db: Session):
        """查询所有活动（按开始时间倒序）"""
        return db.query(EventLecture).filter(
            EventLecture.delete_flag == 0
        ).order_by(EventLecture.start_time.desc()).all()

    @staticmethod
    def register(db: Session, event_id: int, customer_id: int = None,
                 customer_name: str = "", contact: str = ""):
        """活动报名，同时更新活动的当前报名人数"""
        registration = EventRegistration(
            event_id=event_id,
            customer_id=customer_id,
            customer_name=customer_name,
            contact=contact
        )
        db.add(registration)
        event = EventCRUD.get_by_id(db, event_id)
        if event:
            event.current_participants = (event.current_participants or 0) + 1
        return registration

    @staticmethod
    def get_registrations(db: Session, event_id: int):
        """查询活动报名列表"""
        return db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.delete_flag == 0
        ).all()


class ProjectCRUD:
    """课程项目数据访问对象"""

    @staticmethod
    def create(db: Session, **kwargs):
        """创建项目"""
        project = CourseProject(**kwargs)
        db.add(project)
        return project

    @staticmethod
    def get_by_id(db: Session, project_id: int):
        """根据ID查询项目"""
        return db.query(CourseProject).filter(
            CourseProject.id == project_id,
            CourseProject.delete_flag == 0
        ).first()

    @staticmethod
    def get_all(db: Session, category: str = ""):
        """查询所有项目（支持按类别筛选，按排序序号排列）"""
        query = db.query(CourseProject).filter(CourseProject.delete_flag == 0)
        if category:
            query = query.filter(CourseProject.category == category)
        return query.order_by(CourseProject.sort_order).all()
