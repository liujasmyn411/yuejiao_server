"""
粤教服务 - RAG 检索引擎
基于关键词+覆盖度的轻量检索（零外部依赖）
"""
import re
from pathlib import Path
from knowledge_base.loader import load_documents, load_qa_pairs
from knowledge_base.splitter import split_text


class RAGEngine:
    """知识库检索增强生成引擎"""

    def __init__(self, kb_dir: str = None):
        self.kb_dir = kb_dir or str(Path(__file__).resolve().parent.parent / "知识库")
        self.chunks: list[dict] = []
        self.qa_pairs: list[dict] = []
        self._loaded = False

    def load(self, kb_dir: str = None):
        """加载知识库文档并建索引"""
        if kb_dir:
            self.kb_dir = kb_dir

        self.chunks = []
        self.qa_pairs = []

        kb_path = Path(self.kb_dir)
        # 加载问答对文件
        for f in kb_path.glob("**/*问答对*.txt"):
            pairs = load_qa_pairs(str(f))
            self.qa_pairs.extend(pairs)

        # 加载普通文档
        docs = load_documents(self.kb_dir)
        for doc in docs:
            if "问答对" in doc["name"]:
                continue
            chunks = split_text(doc["content"], chunk_size=400, overlap=40)
            for i, chunk in enumerate(chunks):
                self.chunks.append({
                    "source": doc["name"],
                    "content": chunk,
                    "index": i,
                })

        self._loaded = True

    def _ensure_loaded(self):
        if not self._loaded:
            self.load()

    def _tokenize(self, text: str) -> set[str]:
        """中文分词 n-gram"""
        words = set()
        clean = re.sub(r'[^一-鿿\w]', '', text.lower())
        for n in [1, 2, 3]:
            for i in range(len(clean) - n + 1):
                words.add(clean[i:i+n])
        return words

    def _score(self, query_tokens: set, text: str) -> float:
        """相关性打分"""
        text_tokens = self._tokenize(text)
        if not query_tokens:
            return 0
        overlap = len(query_tokens & text_tokens)
        exact = sum(1 for t in query_tokens if len(t) >= 2 and t in text)
        return overlap * 1.0 + exact * 3.0

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """检索最相关的文档片段"""
        self._ensure_loaded()
        query_tokens = self._tokenize(query)

        # 精确问答对匹配优先
        exact_matches = []
        for qa in self.qa_pairs:
            q_score = self._score(query_tokens, qa["question"])
            if query.strip() in qa["question"] or q_score > 8:
                exact_matches.append({
                    "source": "FAQ",
                    "content": f"Q: {qa['question']}\nA: {qa['answer']}",
                    "score": 100.0,
                })

        # 文档片段检索
        scored = []
        for chunk in self.chunks:
            s = self._score(query_tokens, chunk["content"])
            if s > 0:
                scored.append({**chunk, "score": s})

        scored.sort(key=lambda x: x["score"], reverse=True)
        results = exact_matches[:2] + scored[:top_k]
        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]

    def retrieve_context(self, query: str, max_chars: int = 2000) -> str:
        """检索并拼接上下文"""
        results = self.search(query, top_k=5)
        parts = []
        total = 0
        for r in results:
            content = r["content"]
            if total + len(content) > max_chars:
                remaining = max_chars - total
                if remaining > 100:
                    parts.append(content[:remaining])
                break
            parts.append(f"[来源: {r['source']}]\n{content}")
            total += len(content)
        return "\n\n---\n\n".join(parts)


# 全局单例
_rag_engine = None


def get_rag_engine(kb_dir: str = None) -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine(kb_dir)
        _rag_engine.load()
    return _rag_engine
