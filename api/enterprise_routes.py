from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
def get_enterprise_status():
    return {"service": "enterprise", "status": "ok"}
