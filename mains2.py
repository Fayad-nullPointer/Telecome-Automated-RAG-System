# main.py — FastAPI Backend
from os import name

from fastapi import FastAPI
from pydantic import BaseModel
from rag_core import TelecomRAG

app = FastAPI(title="NileTel Arabic AI Assistant")

# Load TelecomRAG once when the server starts
# Constructor builds the full pipeline: load → chunk → embed → index
rag = TelecomRAG()


class QueryRequest(BaseModel):
    """Schema for incoming request"""
    query: str   # The user's question in Arabic


class QueryResponse(BaseModel):
    """Schema for API response"""
    answer: str
    needs_action: str
    sources: list
    displayed_source: str


@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "API is running"}


@app.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest):
    """Main endpoint — runs the full RAG pipeline and returns the response."""
    print(f"\n[API] Received query: {request.query}")

    response = rag.run_rag_pipeline(request.query)

    print(f"[API] Needs Action: {response.get('needs_action', 'NO')}")

    # displayed_source = first source in the list (if any)
    sources = response.get("sources", [])
    displayed_source = sources[0] if sources else ""

    return {
        "answer":           response.get("answer", ""),
        "needs_action":     response.get("needs_action", "NO"),
        "sources":          sources,
        "displayed_source": displayed_source,
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    