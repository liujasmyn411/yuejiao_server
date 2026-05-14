class ApprovalFlow:
    def submit(self, request_data: dict) -> dict:
        return {"status": "submitted", "id": None}

    def check_status(self, request_id: int) -> dict:
        return {"status": "pending", "id": request_id}
