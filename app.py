import os
import streamlit as st
from dotenv import load_dotenv

import document_loader
import vector_store
from rag_pipeline import RAGPipeline

load_dotenv()

st.set_page_config(
    page_title="Domain-Specific RAG Chatbot",
    layout="wide"
)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

if "rag_pipeline" not in st.session_state:
    st.session_state.rag_pipeline = None

if "loaded_documents" not in st.session_state:
    st.session_state.loaded_documents = []

if "chunk_count" not in st.session_state:
    st.session_state.chunk_count = 0

# --- Sidebar ---
st.sidebar.title("Document Upload & Settings")

api_key = os.getenv("GOOGLE_API_KEY", "")
user_api_key = st.sidebar.text_input(
    "Gemini API Key",
    value=api_key,
    type="password",
    help="Enter your Google Gemini API key or set it in .env"
)

uploaded_files = st.sidebar.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

with st.sidebar.expander("Parameters", expanded=False):
    chunk_size = st.slider("Chunk Size", 400, 1500, 800, 50)
    chunk_overlap = st.slider("Chunk Overlap", 50, 300, 120, 10)
    top_k = st.slider("Top K Chunks", 1, 8, 4)

col1, col2 = st.sidebar.columns(2)
process_btn = col1.button("Process", use_container_width=True)
sample_btn = col2.button("Load Sample", use_container_width=True)

if process_btn:
    if not user_api_key:
        st.sidebar.error("Please provide an API key.")
    elif not uploaded_files:
        st.sidebar.error("Please upload at least one PDF.")
    else:
        with st.spinner("Processing documents..."):
            try:
                raw_docs = []
                file_names = []
                for f in uploaded_files:
                    docs = document_loader.load_uploaded_pdf(f)
                    raw_docs.extend(docs)
                    file_names.append(f.name)

                if not raw_docs:
                    st.sidebar.warning("No text could be extracted from the uploaded PDF(s).")
                else:
                    chunks = vector_store.chunk_documents(raw_docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                    embeddings = vector_store.get_embeddings_model(api_key=user_api_key)
                    vs = vector_store.create_vector_store(chunks, embeddings)
                    vector_store.save_vector_store(vs, "vector_store/saved_index")

                    st.session_state.vector_store = vs
                    st.session_state.rag_pipeline = RAGPipeline(vector_store=vs, api_key=user_api_key)
                    st.session_state.loaded_documents = file_names
                    st.session_state.chunk_count = len(chunks)
                    st.sidebar.success(f"Indexed {len(file_names)} file(s) ({len(chunks)} chunks).")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

if sample_btn:
    if not user_api_key:
        st.sidebar.error("Please provide an API key.")
    else:
        sample_path = os.path.join("documents", "company_policy.pdf")
        if not os.path.exists(sample_path):
            st.sidebar.error("Sample document not found at documents/company_policy.pdf")
        else:
            with st.spinner("Loading sample policy document..."):
                try:
                    raw_docs = document_loader.load_pdf_file(sample_path)
                    chunks = vector_store.chunk_documents(raw_docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                    embeddings = vector_store.get_embeddings_model(api_key=user_api_key)
                    vs = vector_store.create_vector_store(chunks, embeddings)

                    st.session_state.vector_store = vs
                    st.session_state.rag_pipeline = RAGPipeline(vector_store=vs, api_key=user_api_key)
                    st.session_state.loaded_documents = ["company_policy.pdf"]
                    st.session_state.chunk_count = len(chunks)
                    st.sidebar.success(f"Loaded company_policy.pdf ({len(chunks)} chunks).")
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")

st.sidebar.divider()
if st.session_state.loaded_documents:
    st.sidebar.write("**Current Documents:**")
    for doc in st.session_state.loaded_documents:
        st.sidebar.write(f"- {doc}")
    st.sidebar.write(f"Total chunks: {st.session_state.chunk_count}")

    if st.sidebar.button("Reset Documents", use_container_width=True):
        st.session_state.vector_store = None
        st.session_state.rag_pipeline = None
        st.session_state.loaded_documents = []
        st.session_state.chunk_count = 0
        st.session_state.messages = []
        st.rerun()

if st.sidebar.button("Clear Chat", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

# --- Main Screen ---
st.title("Domain-Specific RAG Chatbot")
st.write("Ask questions based on your uploaded PDF documents. Answers include source document and page numbers.")
st.caption("Note: Please verify important information directly against the original documents.")

# Sample question buttons if sample is loaded
if "company_policy.pdf" in st.session_state.loaded_documents:
    st.write("**Sample Questions:**")
    sq1, sq2, sq3 = st.columns(3)
    if sq1.button("Core working hours?", use_container_width=True):
        st.session_state.selected_sample_query = "What are the core working hours for employees?"
    if sq2.button("How is attendance calculated?", use_container_width=True):
        st.session_state.selected_sample_query = "How is attendance calculated?"
    if sq3.button("Who is the company CEO?", use_container_width=True):
        st.session_state.selected_sample_query = "Who is the company CEO?"

# Display chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "sources" in msg and msg["sources"]:
            with st.expander("Sources"):
                for src in msg["sources"]:
                    st.write(f"- Document: `{src['source']}`, Page: {src['page']}")
                if "chunks" in msg and msg["chunks"]:
                    st.write("---")
                    for i, chunk in enumerate(msg["chunks"], 1):
                        st.write(f"**Chunk {i} ({chunk['source']} - Page {chunk['page']})**")
                        st.caption(chunk["content"])

user_query = st.chat_input("Enter your question...")
if "selected_sample_query" in st.session_state and st.session_state.selected_sample_query:
    user_query = st.session_state.selected_sample_query
    del st.session_state.selected_sample_query

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.write(user_query)

    if not st.session_state.rag_pipeline:
        bot_reply = "Please upload and process a PDF document (or click 'Load Sample') before asking questions."
        with st.chat_message("assistant"):
            st.warning(bot_reply)
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    else:
        with st.chat_message("assistant"):
            with st.spinner("Searching documents..."):
                try:
                    result = st.session_state.rag_pipeline.answer_question(user_query, top_k=top_k)
                    answer = result["answer"]
                    sources = result["sources"]
                    retrieved_chunks = result["retrieved_chunks"]

                    st.write(answer)
                    if sources:
                        with st.expander("Sources"):
                            for src in sources:
                                st.write(f"- Document: `{src['source']}`, Page: {src['page']}")
                            if retrieved_chunks:
                                st.write("---")
                                for i, chunk in enumerate(retrieved_chunks, 1):
                                    st.write(f"**Chunk {i} ({chunk['source']} - Page {chunk['page']})**")
                                    st.caption(chunk["content"])

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "chunks": retrieved_chunks
                    })
                except Exception as e:
                    err = f"Error generating answer: {e}"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})
