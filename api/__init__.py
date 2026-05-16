from fastapi import APIRouter

from api.system_routes import router as system_router
from api.student_routes import router as student_router
from api.enterprise_routes import router as enterprise_router
from api.customer_routes import router as customer_router
from api.report_routes import router as report_router
from api.chat_routes import router as chat_router

router = APIRouter()
router.include_router(system_router)
router.include_router(chat_router)
router.include_router(student_router)
router.include_router(enterprise_router)
router.include_router(customer_router)
router.include_router(report_router)
