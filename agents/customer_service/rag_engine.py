class RAGEngine:
    def __init__(self):
        pass

    def retrieve(self, query: str):
        return []

    def generate(self, query: str):
        retrieved = self.retrieve(query)
        return {"query": query, "retrieved": retrieved}
