from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
def get_customer_status():
    return {"service": "customer", "status": "ok"}
