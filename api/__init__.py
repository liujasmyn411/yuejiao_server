from fastapi import APIRouter

from api.student_routes import router as student_router
from api.enterprise_routes import router as enterprise_router
from api.customer_routes import router as customer_router

router = APIRouter()
router.include_router(student_router)
router.include_router(enterprise_router)
router.include_router(customer_router)
