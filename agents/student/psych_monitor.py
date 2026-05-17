"""
学生助手 - 心理监测引擎
实时评估学生情绪状态，识别高危信号并触发预警
"""
import json
from utils.llm_client import get_llm_client
from agents.student.prompts import PSYCH_MONITOR_PROMPT, PSYCH_REPLY_PROMPT


class PsychMonitor:
    """留学生心理健康监测与关怀引擎"""

    # 高危触发词（本地快速检测，不依赖LLM）
    HIGH_RISK_KEYWORDS = [
        "不想活", "想死", "自杀", "自残", "结束生命",
        "活不下去", "没意义", "绝望", "没有希望",
        "被欺负", "被打了", "被威胁", "伤害我",
        "崩溃", "撑不住了", "不想活了",
    ]
    MEDIUM_RISK_KEYWORDS = [
        "崩溃", "撑不住", "学不下去", "肯定挂科",
        "没人理解", "没朋友", "好孤独", "想家想疯了",
        "睡不着", "失眠", "吃不下", "一直哭",
        "睡不好", "不想交流", "不想说话", "不想和别人",
        "伤心", "难过", "状态不好", "很糟糕", "没胃口",
        "抑郁", "压力好大", "压力很大", "迷茫", "不知道怎么办",
        "想哭", "烦躁", "无助", "孤独", "想家", "想爸妈", "想回家",
        "怕挂科", "学不懂", "跟不上",
    ]

    def __init__(self):
        self.llm = get_llm_client()

    def evaluate(self, user_input: str) -> dict:
        """评估学生消息的情绪状态和风险等级"""
        # 先做本地关键词快速检测
        quick_check = self._keyword_check(user_input)
        if quick_check["risk_level"] == "high":
            return quick_check

        # LLM 深度评估
        prompt = PSYCH_MONITOR_PROMPT.format(user_input=user_input)
        result = self.llm._call_api(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )
        try:
            parsed = json.loads(result)
            return {
                "emotion_tag": parsed.get("emotion_tag", "平静"),
                "emotion_score": parsed.get("emotion_score", 70),
                "risk_level": parsed.get("risk_level", "none"),
                "trigger_reason": parsed.get("trigger_reason", ""),
            }
        except json.JSONDecodeError:
            # 回退到关键词检测结果
            return quick_check

    def _keyword_check(self, text: str) -> dict:
        """本地关键词快速检测"""
        for kw in self.HIGH_RISK_KEYWORDS:
            if kw in text:
                return {
                    "emotion_tag": "绝望",
                    "emotion_score": 5,
                    "risk_level": "high",
                    "trigger_reason": f"检测到高危关键词: {kw}",
                }
        for kw in self.MEDIUM_RISK_KEYWORDS:
            if kw in text:
                return {
                    "emotion_tag": "焦虑",
                    "emotion_score": 25,
                    "risk_level": "medium",
                    "trigger_reason": f"检测到中危关键词: {kw}",
                }
        return {
            "emotion_tag": "未知",
            "emotion_score": 60,
            "risk_level": "none",
            "trigger_reason": "",
        }

    def generate_reply(self, user_input: str, evaluation: dict) -> str:
        """根据情绪评估结果生成温暖回复"""
        risk = evaluation.get("risk_level", "none")

        risk_guidance = {
            "high": "学生可能有严重心理危机。请极度温和地回应，表达关心，建议联系专业心理咨询师或信任的老师。不要轻描淡写，不要回避问题。",
            "medium": "学生有明显负面情绪。请表达理解和共情，肯定ta的感受，给一些缓解压力的小建议。",
            "low": "学生有轻微情绪波动。用轻松温暖的语气回应，适当鼓励。",
            "none": "学生情绪平稳。正常友好地回应即可。",
        }

        prompt = PSYCH_REPLY_PROMPT.format(
            emotion_tag=evaluation.get("emotion_tag", "平静"),
            emotion_score=evaluation.get("emotion_score", 70),
            risk_level=risk,
            risk_guidance=risk_guidance.get(risk, risk_guidance["none"]),
            user_input=user_input,
        )
        return self.llm.chat(prompt, user_input)

    def should_alert(self, evaluation: dict) -> bool:
        """判断是否需要触发预警"""
        return evaluation.get("risk_level") in ("high", "medium")

    def get_alert_level(self, evaluation: dict) -> str:
        """获取预警等级"""
        return evaluation.get("risk_level", "none")
