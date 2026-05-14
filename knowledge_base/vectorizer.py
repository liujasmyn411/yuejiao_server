from typing import List


def vectorize_texts(texts: List[str]) -> List[List[float]]:
    return [[0.0 for _ in text.split()] for text in texts]
