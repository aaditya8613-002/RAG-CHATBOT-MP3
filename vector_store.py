import os
from typing import List, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_documents(
    documents: List[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 120
) -> List[Document]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    return text_splitter.split_documents(documents)

def get_embeddings_model(api_key: Optional[str] = None):
    effective_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    if effective_key:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=effective_key
            )
        except Exception:
            pass

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    except Exception as e:
        raise RuntimeError(f"Could not load embedding model: {e}")

def create_vector_store(chunks: List[Document], embeddings):
    from langchain_community.vectorstores import FAISS
    if not chunks:
        raise ValueError("Cannot create index from empty chunks.")
    return FAISS.from_documents(chunks, embeddings)

def save_vector_store(vector_store, folder_path: str = "vector_store/saved_index") -> str:
    os.makedirs(folder_path, exist_ok=True)
    vector_store.save_local(folder_path)
    return folder_path

def load_vector_store(folder_path: str = "vector_store/saved_index", embeddings=None):
    from langchain_community.vectorstores import FAISS
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Vector store directory not found: {folder_path}")

    if embeddings is None:
        embeddings = get_embeddings_model()

    return FAISS.load_local(
        folder_path,
        embeddings,
        allow_dangerous_deserialization=True
    )
