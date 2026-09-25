import os
import io
from typing import List, Union
from pypdf import PdfReader
from langchain_core.documents import Document

MAX_FILE_SIZE_MB = 25

def validate_pdf_file(file_name: str, file_size_bytes: int) -> None:
    if not file_name.lower().endswith(".pdf"):
        raise ValueError(f"Invalid file: '{file_name}'. Only PDF files are allowed.")
    
    size_mb = file_size_bytes / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB.")

def extract_text_from_pdf_stream(stream: Union[io.BytesIO, io.BufferedReader], source_name: str) -> List[Document]:
    documents: List[Document] = []
    reader = PdfReader(stream)
    total_pages = len(reader.pages)

    for page_idx, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text()
        except Exception:
            continue

        if not page_text or not page_text.strip():
            continue

        doc = Document(
            page_content=page_text.strip(),
            metadata={
                "source": source_name,
                "page": page_idx,
                "total_pages": total_pages,
            }
        )
        documents.append(doc)

    return documents

def load_pdf_file(file_path: str) -> List[Document]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    validate_pdf_file(file_name, file_size)

    with open(file_path, "rb") as f:
        return extract_text_from_pdf_stream(f, source_name=file_name)

def load_uploaded_pdf(uploaded_file) -> List[Document]:
    file_name = uploaded_file.name
    file_size = uploaded_file.size
    validate_pdf_file(file_name, file_size)

    stream = io.BytesIO(uploaded_file.getvalue())
    return extract_text_from_pdf_stream(stream, source_name=file_name)

def load_multiple_documents(file_sources: List[Union[str, any]]) -> List[Document]:
    all_docs: List[Document] = []
    for item in file_sources:
        if isinstance(item, str):
            docs = load_pdf_file(item)
        else:
            docs = load_uploaded_pdf(item)
        all_docs.extend(docs)
    return all_docs
