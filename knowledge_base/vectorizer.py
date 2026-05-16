"""
粤教服务 - RAG 检索引擎
基于关键词+覆盖度的轻量检索（零外部依赖）
"""
import re
from pathlib import Path
from knowledge_base.loader import load_documents, load_qa_pairs
from knowledge_base.splitter import split_text

# 中文停用词（虚词/标点，对检索无区分度）
_STOP_WORDS = set(
    "的了吗呢吧啊呀嗯么着也在都与及或和从到被把让向对于关于按照通过根据因为所以但是然而虽然不过"
    "可以能够需要应该会可能会必须一定不用不要不能不得"
    "这是一个那只这种那么什么怎么怎样为什么多少哪些哪个哪"
    "上了中下里外前后面左右旁边"
    "很非常比较尤其特别是就是而且不仅还有比如例如等等以及"
    "一二两三四五六七八九十百千万"
)

# 同义词映射：用户口语 → FAQ 书面语
_SYNONYMS = {
    "名字": ["简称", "名称", "叫什么", "全称"],
    "叫什么": ["简称", "名称", "全称"],
    "好在哪": ["优势", "特点", "好处"],
    "好在": ["优势", "特点", "好处"],
    "咋样": ["怎么样", "如何", "优势"],
    "咋": ["怎么", "如何"],
    "报名咋": ["报名流程", "怎么报名"],
    "咋报名": ["报名流程", "怎么报名"],
    "退钱": ["退费", "退款"],
    "能退": ["退费", "退款"],
    "退款": ["退费"],
    "办签证": ["签证", "签证申请", "签证流程"],
    "签证咋办": ["签证流程", "签证申请", "签证办理"],
    "怎么办": ["办理", "申请", "流程"],
    "怎么报名": ["报名流程", "如何报名"],
    "如何报名": ["报名流程"],
    "在哪": ["地址", "位置", "在哪办公"],
    "电话": ["联系方式", "热线", "联系电话"],
    "找谁": ["联系人", "负责人", "咨询"],
    "要什么": ["需要", "要求", "条件"],
    "要什么条件": ["报名条件", "申请条件", "要求"],
    "要多少": ["费用", "学费", "价格"],
    "多少钱": ["学费", "费用", "价格", "收费", "总计"],
    "总共": ["总计", "合计", "全部费用"],
    "贵不贵": ["学费", "费用"],
    "贵吗": ["学费", "费用"],
    "回国认可": ["学历认证", "教育部认证", "认可"],
    "承认吗": ["认证", "认可"],
    "认不认": ["认证", "认可"],
    "好吗": ["优势", "特点"],
}

# 商业/教育领域高频词（不应被停用）
_KEEP_WORDS = {"本科", "硕士", "博士", "专科", "大专", "中专", "高中", "初中", "小学",
               "德国", "新加坡", "英国", "美国", "加拿大", "澳大利亚", "中国",
               "留学", "签证", "学费", "报名", "项目", "课程", "专业", "学历",
               "双元制", "本硕", "专升本", "专升硕", "国际", "教育"}


class RAGEngine:
    """知识库检索增强生成引擎"""

    def __init__(self, kb_dir: str = None):
        self.kb_dir = kb_dir or str(Path(__file__).resolve().parent / "data")
        self.chunks: list[dict] = []
        self.qa_pairs: list[dict] = []
        self._faq_tokens: list[set] = []  # 预计算 FAQ 问题 token，加速检索
        self._loaded = False

    def load(self, kb_dir: str = None):
        """加载知识库文档并建索引"""
        if kb_dir:
            self.kb_dir = kb_dir

        self.chunks = []
        self.qa_pairs = []
        self._faq_tokens = []
        self._keyword_index: dict[str, set] = {}  # 关键词 → FAQ 索引集合

        kb_path = Path(self.kb_dir)

        # 加载问答对文件
        for f in kb_path.glob("**/*问答对*.txt"):
            pairs = load_qa_pairs(str(f))
            self.qa_pairs.extend(pairs)

        # 预计算 FAQ 问题 token + 关键词倒排索引
        for idx, qa in enumerate(self.qa_pairs):
            tokens = self._tokenize(qa["question"])
            self._faq_tokens.append(tokens)
            # 建立倒排索引：2-3字词 → 包含它的 FAQ 编号
            for t in tokens:
                if len(t) >= 2:
                    if t not in self._keyword_index:
                        self._keyword_index[t] = set()
                    self._keyword_index[t].add(idx)

        # 加载普通文档（不含"问答对"的文件）
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
        """中文分词 n-gram，过滤停用词和噪声（纯 tokenizer，不做同义词展开）"""
        words = set()
        clean = re.sub(r'[^一-鿿\w]', '', text.lower())
        for n in [1, 2, 3]:
            for i in range(len(clean) - n + 1):
                gram = clean[i:i + n]
                if n == 1 and gram in _STOP_WORDS and gram not in _KEEP_WORDS:
                    continue
                if n == 2:
                    if all(c in _STOP_WORDS for c in gram):
                        continue
                    cs = sum(1 for c in gram if c in _STOP_WORDS)
                    if cs >= 2:
                        continue
                if n == 3 and any(c in _STOP_WORDS for c in gram):
                    continue
                words.add(gram)
        return words

    def _tokenize_query(self, text: str) -> tuple[set[str], set[str]]:
        """查询专用 tokenize：返回 (全量tokens, 同义词tokens)"""
        tokens = self._tokenize(text)
        clean = re.sub(r'[^一-鿿\w]', '', text.lower())

        syn_tokens: set[str] = set()
        for slang, formal_list in _SYNONYMS.items():
            if slang in clean:
                for formal in formal_list:
                    syn_tokens.add(formal)
                    tokens.add(formal)
        return tokens, syn_tokens

    def _jaccard(self, a: set, b: set) -> float:
        """Jaccard 相似度"""
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _score(self, query_tokens: set, text: str) -> float:
        """相关性打分：Jaccard 相似度 + 精确词组加权"""
        text_tokens = self._tokenize(text)
        if not query_tokens:
            return 0

        # 基础 Jaccard
        base = self._jaccard(query_tokens, text_tokens)

        # 精确词组加权：查询中的连续 2-gram 在文本中原样出现一次 +0.05
        bonus = 0.0
        for t in query_tokens:
            if len(t) >= 2 and t in text:
                bonus += 0.05
        bonus = min(bonus, 0.3)  # 上限 0.3，避免长查询过度加权

        return base + bonus

    def _idf_weight(self, token: str) -> float:
        """简易 IDF：token 在 FAQ 中出现次数越少，权重越高"""
        if not hasattr(self, '_idf_cache'):
            self._idf_cache = {}
            total = max(len(self.qa_pairs), 1)
            for t in self._all_faq_tokens():
                self._idf_cache[t] = self._idf_cache.get(t, 0) + 1
            for t in self._idf_cache:
                self._idf_cache[t] = 1.0 / (1.0 + self._idf_cache[t] / total * 10)
        return self._idf_cache.get(token, 0.5)

    def _all_faq_tokens(self):
        for tokens in self._faq_tokens:
            yield from tokens

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """检索最相关的 FAQ 和文档片段"""
        self._ensure_loaded()
        query_tokens, syn_tokens = self._tokenize_query(query)
        query_clean = query.strip()

        # 查询中的核心词（>=2字）
        core_tokens = {t for t in query_tokens if len(t) >= 2}
        if not core_tokens:
            core_tokens = query_tokens  # 兜底

        # 同义词核心词 vs n-gram 核心词
        syn_core = core_tokens & syn_tokens
        ngram_core = core_tokens - syn_tokens

        # ── 倒排索引：限定候选 FAQ（并集 + 命中核心词计数） ──
        candidate_hits: dict[int, int] = {}  # idx → 命中核心词数
        for t in core_tokens:
            if t in self._keyword_index:
                for idx in self._keyword_index[t]:
                    candidate_hits[idx] = candidate_hits.get(idx, 0) + 1
        # 至少命中 1 个核心词即可进入候选（倒排索引保证相关性，由 scoring 排序）
        candidate_ids = set(candidate_hits.keys())
        if not candidate_ids:
            candidate_ids = set(range(len(self.qa_pairs)))

        # ── FAQ 匹配（覆盖率 + IDF 加权，仅评估候选） ──
        faq_results = []
        for idx in candidate_ids:
            qa = self.qa_pairs[idx]
            q_tokens = self._faq_tokens[idx]
            question = qa["question"]

            # 同义词覆盖率（业务关键词）
            syn_total = sum(self._idf_weight(t) for t in syn_core)
            syn_hit = sum(self._idf_weight(t) for t in syn_core if t in question)
            syn_coverage = syn_hit / syn_total if syn_total > 0 else 1.0

            # n-gram 覆盖率（辅助匹配）
            ngram_total = sum(self._idf_weight(t) for t in ngram_core)
            ngram_hit = sum(self._idf_weight(t) for t in ngram_core if t in question)
            ngram_coverage = ngram_hit / ngram_total if ngram_total > 0 else 1.0

            # 综合：同义词权重 0.6，n-gram 0.4
            coverage = syn_coverage * 0.6 + ngram_coverage * 0.4

            # 精确子串匹配额外加分
            substring_bonus = 0.0
            if query_clean and len(query_clean) >= 2 and query_clean in question:
                substring_bonus = 0.3
            elif query_clean and len(query_clean) >= 2 and question in query_clean:
                substring_bonus = 0.15

            # Jaccard 作为辅助（两边都有的词 vs 总词数）
            jac = self._jaccard(query_tokens, q_tokens)

            # 核心词命中数加分（同义词命中 3x，n-gram 1x，抑制噪声）
            syn_hits = sum(3 for t in syn_core if t in question)
            ngram_hits = sum(1 for t in ngram_core if t in question)
            max_possible = len(syn_core) * 3 + len(ngram_core)
            hit_count_bonus = min((syn_hits + ngram_hits) / max(max_possible, 1), 1.0) * 0.15

            # 综合分：覆盖率主导 + Jaccard 辅助 + 命中数 + 精确匹配加成
            faq_score = coverage * 0.45 + jac * 0.15 + hit_count_bonus + substring_bonus
            faq_score = min(faq_score, 1.0)

            if faq_score > 0.10:
                faq_results.append({
                    "source": "FAQ",
                    "content": f"Q: {question}\nA: {qa['answer']}",
                    "score": round(faq_score * 100, 1),
                })

        faq_results.sort(key=lambda x: x["score"], reverse=True)

        # ── 文档片段匹配 ──
        doc_results = []
        for chunk in self.chunks:
            s = self._score(query_tokens, chunk["content"])
            if s > 0.05:
                doc_results.append({**chunk, "score": round(s * 100, 1)})

        doc_results.sort(key=lambda x: x["score"], reverse=True)

        merged = faq_results[:4] + doc_results[:top_k]
        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged[:top_k]

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
