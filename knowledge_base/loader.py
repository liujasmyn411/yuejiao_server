from pathlib import Path


def load_documents(directory: str):
    path = Path(directory)
    documents = []
    for file_path in path.glob("**/*"):
        if file_path.is_file():
            documents.append({"path": str(file_path), "content": file_path.read_text(encoding="utf-8")})
    return documents
