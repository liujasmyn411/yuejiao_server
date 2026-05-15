"""
粤教服务 - 大模型统一调用客户端
支持 OpenAI 兼容接口（GPT / DeepSeek / 通义千问等）
"""
import json
import requests
from config import settings


class LLMClient:
    """OpenAI 兼容的 LLM 调用客户端"""

    def __init__(self):
        self.api_base = getattr(settings, 'openai_api_base', 'https://api.openai.com/v1')
        self.api_key = settings.openai_api_key
        self.model = settings.model_name
        self.max_tokens = getattr(settings, 'openai_max_tokens', 2000)
        self.temperature = getattr(settings, 'openai_temperature', 0.7)

    def _call_api(self, messages: list, temperature: float = None, max_tokens: int = None) -> str:
        """调用 OpenAI 兼容接口"""
        if not self.api_key or self.api_key.startswith("sk-your-"):
            return "[LLM未配置API Key，使用本地规则引擎]"

        try:
            resp = requests.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature or self.temperature,
                    "max_tokens": max_tokens or self.max_tokens,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM调用失败: {e}]"

    def chat(self, system_prompt: str, user_message: str) -> str:
        """单轮对话"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        return self._call_api(messages)

    def classify_intent(self, user_input: str, intents: dict) -> dict:
        """意图识别 —— 根据用户输入判断意图类别"""
        intent_list = "\n".join(f"- {k}: {v}" for k, v in intents.items())
        prompt = f"""你是一个意图识别分类器。根据用户输入，判断其意图。

可选意图：
{intent_list}

用户输入：{user_input}

请以JSON格式返回，不要输出其他内容：
{{"intent": "意图名称", "confidence": 0.0-1.0, "entities": {{}}}}"""

        result = self._call_api(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"intent": "fallback", "confidence": 0.3, "entities": {}}

    def extract_info(self, user_input: str, fields: list) -> dict:
        """从用户输入中提取结构化信息"""
        prompt = f"""从以下用户输入中提取信息，返回JSON格式。

需要提取的字段：{json.dumps(fields, ensure_ascii=False)}

用户输入：{user_input}

只返回JSON，不要其他内容。"""

        result = self._call_api(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {f: None for f in fields}

    def generate_report(self, report_type: str, data: dict) -> str:
        """根据数据生成分析报告"""
        prompt = f"""你是一个数据分析师。根据以下数据生成一份{report_type}。

数据：{json.dumps(data, ensure_ascii=False, default=str)}

要求：
1. 使用中文
2. 包含数据概述、关键发现、趋势洞察
3. 给出可操作的改进建议
4. 格式清晰，使用Markdown"""

        return self._call_api(
            [{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1500,
        )


# 全局单例
_llm_client = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
