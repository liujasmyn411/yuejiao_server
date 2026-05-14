from typing import Dict


class CustomerServiceAgent:
    def __init__(self):
        self.name = "customer_service_agent"

    def route_intent(self, user_input: str) -> Dict[str, str]:
        return {"intent": "unknown", "response": "This is a stub response."}
