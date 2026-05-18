"""
企业助手 - 语音处理器
语音转文字 + 口述→结构化日报
"""
import json
import base64
import logging
from datetime import date
from utils.llm_client import get_llm_client
from agents.enterprise.prompts import REPORT_PROMPT
from config import settings

logger = logging.getLogger("yuejiao.voice")


class VoiceProcessor:
    """语音处理：转写 + 日报结构化"""

    def __init__(self):
        self.llm = get_llm_client()

    def transcribe(self, audio_bytes: bytes = None) -> str:
        """语音转文字（Whisper API，复用 openai_api_key 和 openai_api_base）"""
        if not audio_bytes:
            return ""
        if not settings.openai_api_key:
            return "[语音转写不可用：未配置API Key]"

        try:
            import requests
            # Whisper API endpoint: {base}/audio/transcriptions
            base = settings.openai_api_base.rstrip("/")
            url = f"{base}/audio/transcriptions"

            headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
            files = {
                "file": ("audio.wav", audio_bytes, "audio/wav"),
                "model": (None, "whisper-1"),
            }
            resp = requests.post(url, headers=headers, files=files, timeout=60)
            resp.raise_for_status()
            return resp.json().get("text", "")
        except Exception as e:
            logger.error(f"语音转写失败: {e}")
            return f"[语音转写失败: {e}]"

    def synthesize(self, text: str) -> bytes:
        """文字转语音（OpenAI TTS API，复用 openai_api_key 和 openai_api_base）"""
        if not text:
            return b""
        if not settings.openai_api_key:
            return b""

        try:
            import requests
            base = settings.openai_api_base.rstrip("/")
            url = f"{base}/audio/speech"

            payload = {
                "model": "tts-1",
                "input": text,
                "voice": "alloy",
            }
            headers = {
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            return b""

    def text_to_report(self, oral_text: str) -> dict:
        """将口述文本整理为结构化日报"""
        prompt = REPORT_PROMPT + "\n" + oral_text
        result = self.llm._call_api(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
        )

        info = self.llm.extract_info(
            oral_text,
            ["日期", "工作类型", "客户名称列表", "待办事项"]
        )

        # LLM 返回的字段可能为 list，统一转换为字符串，防止前端/后端 422
        def _to_str(val, sep=","):
            if val is None:
                return ""
            if isinstance(val, list):
                return sep.join(str(v) for v in val if v is not None)
            return str(val)

        work_type = info.get("工作类型", "日常工作") or "日常工作"
        return {
            "report_date": self._normalize_date(info.get("日期")),
            "work_type": _to_str(work_type, ","),
            "summary": result.strip(),
            "raw_text": oral_text,
            "customers_mentioned": _to_str(info.get("客户名称列表"), ","),
            "todos": _to_str(info.get("待办事项"), "；"),
        }

    @staticmethod
    def _normalize_date(date_str) -> str:
        """将 LLM 提取的日期规范化成 YYYY-MM-DD 格式"""
        import re
        from datetime import datetime, timedelta
        if not date_str:
            return date.today().strftime("%Y-%m-%d")
        date_str = str(date_str).strip()
        # 已经是标准格式
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return date_str
        today = date.today()
        # 中文相对日期
        if date_str in ("今天", "今日"):
            return today.strftime("%Y-%m-%d")
        if date_str in ("昨天", "昨日"):
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        if date_str in ("明天", "明日"):
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        # 尝试其他常见格式
        for fmt in ("%Y年%m月%d日", "%Y/%m/%d", "%m月%d日", "%m-%d"):
            try:
                parsed = datetime.strptime(date_str, fmt)
                if fmt in ("%m月%d日", "%m-%d"):
                    parsed = parsed.replace(year=today.year)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return today.strftime("%Y-%m-%d")

    def summarize_reports(self, reports: list) -> str:
        """将多份日报汇总为周报/阶段总结"""
        if not reports:
            return "暂无日报数据"

        reports_text = "\n\n".join(
            f"[{r.get('report_date', '')}] {r.get('content', '')}"
            for r in reports
        )
        prompt = f"""你是一位团队负责人。请将以下员工的日报汇总为一份周报总结。

要求：
1. 概括本周核心工作亮点
2. 按客户/项目维度汇总进展
3. 识别风险和待解决问题
4. 给出下周工作建议

日报列表：
{reports_text}

请用Markdown格式输出周报。"""

        return self.llm._call_api(
            [{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1200,
        )
