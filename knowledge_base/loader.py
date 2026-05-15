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
    """加载问答对格式的文件（Q: ... A: ... 格式）"""
    path = Path(file_path)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    pairs = []
    # 匹配 Q: 和 A: 的问答对
    pattern = re.compile(r'Q[：:]\s*(.+?)\s*A[：:]\s*(.+?)(?=Q[：:]|\Z)', re.DOTALL)
    for match in pattern.finditer(text):
        pairs.append({
            "question": match.group(1).strip(),
            "answer": match.group(2).strip(),
        })
    return pairs
