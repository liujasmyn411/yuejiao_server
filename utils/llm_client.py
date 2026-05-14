from config import settings


class LLMClient:
    def __init__(self):
        self.api_key = settings.openai_api_key

    def call(self, prompt: str):
        return {"output": "LLM response stub."}
