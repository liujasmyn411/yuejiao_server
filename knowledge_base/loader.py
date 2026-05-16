"""
粤教服务 - 知识库文档加载器
加载知识库目录下的所有文本文件
"""
import re
from pathlib import Path


def load_documents(directory: str) -> list[dict]:
    """加载目录下所有文本文档"""
    path = Path(directory)
    if not path.exists():
        return []
    documents = []
    for file_path in sorted(path.glob("**/*")):
        if file_path.is_file() and file_path.suffix in (".txt", ".md", ".csv"):
            try:
                content = file_path.read_text(encoding="utf-8")
                if content.strip():
                    documents.append({
                        "path": str(file_path),
                        "name": file_path.stem,
                        "content": content,
                    })
            except Exception:
                continue
    return documents


def load_qa_pairs(file_path: str) -> list[dict]:
    """加载问答对文件，自动识别格式：
    - tab 分隔格式：Q\\t\\tA
    - Q: / A: 标记格式
    """
    path = Path(file_path)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    pairs = []

    # 格式1：tab 分隔（Q\\t\\tA，每行一对）
    if "\t" in text:
        for line in text.strip().split("\n"):
            parts = line.split("\t")
            q_part = ""
            a_part = ""
            # 跳过前导空白列，找到第一个非空作为 Q，最后一个非空作为 A
            non_empty = [p for p in parts if p.strip()]
            if len(non_empty) >= 2:
                q_part = non_empty[0].strip()
                a_part = non_empty[-1].strip()
            elif len(non_empty) == 1:
                continue  # 只有问题没有答案，跳过
            if q_part and a_part:
                pairs.append({"question": q_part, "answer": a_part})

    # 格式2：Q: ... A: ... 标记格式
    if not pairs:
        pattern = re.compile(r'Q[：:]\s*(.+?)\s*A[：:]\s*(.+?)(?=Q[：:]|\Z)', re.DOTALL)
        for match in pattern.finditer(text):
            pairs.append({
                "question": match.group(1).strip(),
                "answer": match.group(2).strip(),
            })
    return pairs
