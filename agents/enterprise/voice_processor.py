"""
企业助手 - 语音处理器
语音转文字 + 口述→结构化日报
"""
import json
from datetime import date
from utils.llm_client import get_llm_client
from agents.enterprise.prompts import REPORT_PROMPT


class VoiceProcessor:
    """语音处理：转写 + 日报结构化"""

    def __init__(self):
        self.llm = get_llm_client()

    def transcribe(self, audio_bytes: bytes = None) -> str:
        """语音转文字（需要接入Whisper/讯飞等ASR服务）"""
        return ""

    def synthesize(self, text: str) -> bytes:
        """文字转语音（需要接入TTS服务）"""
        return b""

    def text_to_report(self, oral_text: str) -> dict:
        """将口述文本整理为结构化日报"""
        prompt = REPORT_PROMPT + "\n" + oral_text
        result = self.llm._call_api(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
        )

        # 提取关键信息
        info = self.llm.extract_info(
            oral_text,
            ["日期", "工作类型", "客户名称列表", "待办事项"]
        )

        return {
            "report_date": info.get("日期") or date.today().strftime("%Y-%m-%d"),
            "work_type": info.get("工作类型", "日常工作"),
            "summary": result.strip(),
            "raw_text": oral_text,
            "customers_mentioned": info.get("客户名称列表", ""),
            "todos": info.get("待办事项", ""),
        }

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
