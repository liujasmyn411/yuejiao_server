"""
日期时间解析 —— 将中文相对时间表达（明天/后天/下周一等）转为标准 datetime
"""
import re
from datetime import datetime, timedelta

_WEEKDAYS_CN = {
    "周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6,
    "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3, "星期五": 4, "星期六": 5, "星期日": 6,
}

_TIME_PERIOD = {
    "上午": "09:00", "中午": "12:00", "下午": "14:00", "傍晚": "18:00",
    "晚上": "20:00", "早上": "08:00", "凌晨": "00:00",
}


def normalize_datetime(text: str) -> datetime | None:
    """
    将中文日期表达转为 datetime 对象。
    支持：明天、后天、今天、下周一、本周五、3天后 等
    返回 None 表示无法解析。
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # 已经是标准格式 → 直接解析
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    now = datetime.now()
    base_date = now.date()
    hour = 9
    minute = 0

    # 提取时间段
    for period, time_str in _TIME_PERIOD.items():
        if period in text:
            h, m = time_str.split(":")
            hour, minute = int(h), int(m)
            text = text.replace(period, "")
            break

    text = text.strip()

    # 今天 / 明天 / 后天
    if text == "今天":
        base_date = now.date()
    elif text == "明天":
        base_date = now.date() + timedelta(days=1)
    elif text == "后天":
        base_date = now.date() + timedelta(days=2)
    elif text == "大后天":
        base_date = now.date() + timedelta(days=3)
    elif text == "昨天":
        base_date = now.date() - timedelta(days=1)

    # X天后 / X周后
    m = re.match(r'(\d+)\s*天后?$', text)
    if m:
        base_date = now.date() + timedelta(days=int(m.group(1)))
    m = re.match(r'(\d+)\s*周后?$', text)
    if m:
        base_date = now.date() + timedelta(weeks=int(m.group(1)))

    # 下周X / 本周X / 下周一
    m = re.match(r'(下周|本周|这周)\s*(.+)', text)
    if m:
        scope = m.group(1)
        day_str = m.group(2)
        if day_str in _WEEKDAYS_CN:
            target_wd = _WEEKDAYS_CN[day_str]
            today_wd = now.weekday()
            if scope in ("本周", "这周"):
                delta = target_wd - today_wd
                if delta < 0:
                    delta = 0  # 本周已过的天，当作今天
            else:  # 下周
                delta = 7 - today_wd + target_wd
            base_date = now.date() + timedelta(days=delta)

    # 下个月 / 下月X号
    m = re.match(r'下月(\d+)号?$', text)
    if m:
        day = int(m.group(1))
        if now.month == 12:
            base_date = datetime(now.year + 1, 1, day).date()
        else:
            base_date = datetime(now.year, now.month + 1, day).date()

    # 本月X号 / X号
    m = re.match(r'^(?:本月)?(\d{1,2})号?$', text)
    if m:
        day = int(m.group(1))
        try:
            base_date = datetime(now.year, now.month, day).date()
        except ValueError:
            pass

    # 月-日 格式 (如 "5-20", "05-20")
    m = re.match(r'^(\d{1,2})-(\d{1,2})$', text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        try:
            base_date = datetime(now.year, month, day).date()
        except ValueError:
            pass

    # 日期-时间组合: "明天 14:00", "后天 下午"
    m = re.match(r'^(\d{1,2}):(\d{2})$', text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))

    return datetime(base_date.year, base_date.month, base_date.day, hour, minute)
