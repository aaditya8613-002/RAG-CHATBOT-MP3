"""Integration test for the RAG pipeline.
Tests document loading, chunking, FAISS indexing, similarity retrieval, and question answering.
"""

import os
import sys
from dotenv import load_dotenv

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

import document_loader
import vector_store
from rag_pipeline import RAGPipeline

def run_test():
    print("--- 1. Testing Document Ingestion ---")
    docs = document_loader.load_pdf_file("documents/company_policy.pdf")
    print(f"Loaded {len(docs)} pages from company_policy.pdf")
    assert len(docs) == 5, "Expected 5 pages"

    print("\n--- 2. Testing Chunking ---")
    chunks = vector_store.chunk_documents(docs, chunk_size=800, chunk_overlap=120)
    print(f"Generated {len(chunks)} chunks")
    assert len(chunks) >= 5, "Expected at least 5 chunks"

    print("\n--- 3. Testing FAISS Vector Store Creation ---")
    embeddings = vector_store.get_embeddings_model()
    vs = vector_store.create_vector_store(chunks, embeddings)
    print("FAISS vector store created successfully")

    print("\n--- 4. Testing Index Persistence ---")
    saved_path = vector_store.save_vector_store(vs, "vector_store/saved_index")
    print(f"Vector store saved to: {saved_path}")
    loaded_vs = vector_store.load_vector_store("vector_store/saved_index", embeddings)
    print("Vector store reloaded from disk successfully")

    print("\n--- 5. Testing RAG Pipeline Q&A ---")
    pipeline = RAGPipeline(vector_store=loaded_vs)

    test_queries = [
        "What are the core working hours for employees?",
        "How is attendance calculated?",
        "Who is the company CEO?"
    ]

    for q in test_queries:
        print(f"\n[Query]: {q}")
        res = pipeline.answer_question(q, top_k=3)
        print(f"[Answer]: {res['answer']}")
        print(f"[Sources]: {res['sources']}")

    print("\nAll integration tests passed successfully!")

if __name__ == "__main__":
    run_test()
