"""
粤教服务 - 文本切片器
将长文档切分为重叠的语义块
"""
import re


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """按字符数切片，尽量在句子边界断开"""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break

        # 尝试在句号、换行等自然断点处切开
        chunk = text[start:end]
        for sep in ["\n\n", "\n", "。", "；", "！", "？", ". ", "; "]:
            last = chunk.rfind(sep)
            if last > chunk_size // 2:
                end = start + last + len(sep)
                break

        chunks.append(text[start:end].strip())
        start = end - overlap
        if start >= len(text):
            break

    return [c for c in chunks if c]


def split_by_sections(text: str) -> list[dict]:
    """按章节标题拆分，返回带标题的段落"""
    sections = re.split(r'\n(#{1,3}\s+.+?)\n', text)
    result = []
    current_title = ""
    for i, part in enumerate(sections):
        if re.match(r'^#{1,3}\s+', part):
            current_title = part.replace("#", "").strip()
        elif part.strip():
            result.append({"title": current_title, "content": part.strip()})
    if not result:
        result.append({"title": "", "content": text})
    return result
