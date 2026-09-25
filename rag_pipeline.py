import os
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from prompt import get_rag_prompt

FALLBACK_MESSAGE = "I could not find this information in the uploaded documents."

class RAGPipeline:
    def __init__(self, vector_store, llm=None, api_key: Optional[str] = None):
        self.vector_store = vector_store
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

        if llm is not None:
            self.llm = llm
        else:
            if not self.api_key:
                raise ValueError("API key not found. Please provide GOOGLE_API_KEY.")

            self.candidate_models = [
                "gemini-3.5-flash-lite",
                "gemini-3.5-flash",
                "gemini-3.6-flash",
                "gemini-flash-latest",
            ]
            self.llm = ChatGoogleGenerativeAI(
                model=self.candidate_models[0],
                google_api_key=self.api_key,
                temperature=0.0
            )

        self.prompt_template = get_rag_prompt()

    def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        if not self.vector_store:
            raise ValueError("Vector store has not been initialized.")

        results = self.vector_store.similarity_search_with_score(query, k=top_k)
        retrieved_items = []

        for doc, score in results:
            retrieved_items.append({
                "document": doc,
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Document"),
                "page": doc.metadata.get("page", 1),
                "score": float(score)
            })

        return retrieved_items

    def answer_question(self, query: str, top_k: int = 4) -> Dict[str, Any]:
        retrieved_items = self.retrieve(query, top_k=top_k)

        if not retrieved_items:
            return {
                "answer": FALLBACK_MESSAGE,
                "sources": [],
                "retrieved_chunks": []
            }

        # Build context string with source and page annotations
        context_parts = []
        for i, item in enumerate(retrieved_items, 1):
            src = item["source"]
            pg = item["page"]
            text = item["content"]
            context_parts.append(f"[Passage {i} - {src}, Page {pg}]\n{text}")

        formatted_context = "\n\n".join(context_parts)

        # Call Gemini model
        response = None
        last_error = None
        models = getattr(self, "candidate_models", ["gemini-3.5-flash-lite"])

        for model_name in models:
            try:
                active_llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=self.api_key,
                    temperature=0.0
                )
                chain = self.prompt_template | active_llm
                response = chain.invoke({
                    "context": formatted_context,
                    "question": query
                })
                break
            except Exception as e:
                last_error = e

        if response is None:
            raise RuntimeError(f"Failed to generate answer: {last_error}")

        answer_text = response.content
        if isinstance(answer_text, list):
            extracted = []
            for item in answer_text:
                if isinstance(item, dict) and "text" in item:
                    extracted.append(item["text"])
                elif isinstance(item, str):
                    extracted.append(item)
                else:
                    extracted.append(str(item))
            answer_text = "\n".join(extracted)
        answer_text = str(answer_text).strip()

        # Collect unique sources
        unique_sources = []
        seen = set()
        for item in retrieved_items:
            key = (item["source"], item["page"])
            if key not in seen:
                seen.add(key)
                unique_sources.append({
                    "source": item["source"],
                    "page": item["page"]
                })

        return {
            "answer": answer_text,
            "sources": unique_sources,
            "retrieved_chunks": retrieved_items
        }
