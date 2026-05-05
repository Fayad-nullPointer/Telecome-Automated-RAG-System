import os
import re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv

DATA_PATH       = r"/media/ahmed-fayad/3b40def2-87b7-41ce-8913-2981f887941c/home/ITI Cont.../Guided Project RAG/data"
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ============================================================
# 1. CHUNKING  — copied verbatim
# ============================================================
def chunk_text(text):
    """Splits long documents into smaller paragraphs."""
    paragraphs = re.split(r"\n\s*\n", text.strip())

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) > 700:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


# ============================================================
# 2. EMBEDDINGS  — copied verbatim
# ============================================================
def create_embeddings(chunks):
    """Converts text chunks into vector embeddings."""
    print("Creating embeddings...")

    model = SentenceTransformer(EMBEDDING_MODEL)

    embeddings = model.encode(chunks, normalize_embeddings=True, show_progress_bar=True)

    embeddings = np.array(embeddings).astype("float32")

    print("Embeddings created successfully!")
    print(f"Embedding shape: {embeddings.shape}")

    return model, embeddings


# ============================================================
# 3. FAISS INDEX  — copied verbatim
# ============================================================
def build_faiss_index(embeddings):
    """Builds FAISS index for fast similarity search."""
    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print("FAISS index built successfully!")
    print(f"Total vectors: {index.ntotal}")

    return index


# ============================================================
# 4. RETRIEVAL  — copied verbatim
# ============================================================
def retrieve(query, model, index, chunks, metadata, top_k=6):
    """Retrieves the most relevant chunks for a given query."""
    print(f"\nSearching for: {query}")

    query_emb = model.encode([query], normalize_embeddings=True)
    query_emb = np.array(query_emb).astype("float32")

    distances, indices = index.search(query_emb, top_k)

    results = []
    for idx, score in zip(indices[0], distances[0]):
        if score > 0.4:
            results.append(
                {
                    "text": chunks[idx],
                    "source": metadata[idx]["source"],
                    "score": float(score),
                }
            )

    print(f"Found {len(results)} results")
    return results


# ============================================================
# 5. ROUTING  — copied verbatim
# ============================================================
def route_query(query):
    """
    LLM-based routing function using a small language model.
    Returns one of: "chat" | "out_of_scope" | "ticket"
    """
    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = """أنت نظام توجيه آلي (Router) لشركة اتصالات (NileTel).
مهمتك هي تصنيف رسالة المستخدم إلى فئة واحدة فقط:
- "out_of_scope": مواضيع خارج الاتصالات والدعم الفني (رياضة، أخبار، فضاء، إلخ).
- "ticket": المستخدم يطلب صراحة إنشاء تذكرة، أو إرسال فني، أو تصعيد عطل مستمر.
- "chat": أي سؤال فني، استفسار عن الباقات، طلب مساعدة، أو تحية.

رجاءً قم بالرد بكلمة واحدة فقط وبكل دقة: إما chat أو out_of_scope أو ticket."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"رسالة المستخدم: {query}"},
            ],
            temperature=0.0,
            max_tokens=10,
        )
        route_result = response.choices[0].message.content.strip().lower()

        if "out_of_scope" in route_result:
            return "out_of_scope"
        elif "ticket" in route_result:
            return "ticket"
        else:
            return "chat"
    except Exception as e:
        print(f"Routing error fallback to chat: {e}")
        return "chat"


# ============================================================
# 6. GENERATE ANSWER  — copied verbatim
# ============================================================
def generate_answer(query, retrieved_results):
    """
    Takes the user query and retrieved chunks, builds a prompt,
    sends it to Groq, and returns the final answer + needs_action flag.
    """
    if not retrieved_results:
        return {
            "answer": "مش متأكد من البيانات المتاحة يا فندم.",
            "needs_action": "NO",
            "sources": [],
        }

    context = "\n\n".join(
        [f"Source: {res['source']}\n{res['text']}" for res in retrieved_results]
    )

    client = Groq(api_key=GROQ_API_KEY)

    # --- Chain Link 1: Classify ---
    classification_system = """أنت خبير تحليل طلبات في قسم خدمة العملاء بشركة NileTel للاتصالات.
مهمتك هي تحليل سؤال العميل وتحديد ما إذا كان يتطلب اتخاذ إجراء تقني (مثل: فتح تذكرة، حجز فني، أو تصعيد مشكلة) أم أنه مجرد استفسار عن معلومة.

أمثلة:
- "النت عندي فاصل وعاوز فني" -> YES
- "هو باقة الـ 200 جيجا بكام؟" -> NO"""

    classification_user = f"""سؤال العميل: "{query}"

قم بالرد بكلمة واحدة فقط بناءً على احتياج العميل لإجراء: YES أو NO."""

    class_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": classification_system},
            {"role": "user", "content": classification_user},
        ],
        max_tokens=10,
        temperature=0.0,
    )

    action_needed_str = class_response.choices[0].message.content.strip().upper()
    needs_action = "YES" if re.search(r"YES", action_needed_str) else "NO"

    # --- Chain Link 2: Generate ---
    generation_system = f"""أنت مساعد دعم عملاء محترف وودود في شركة NileTel للاتصالات.

تعليمات الرد:
1. بناءً على حالة الطلب (الموضحة من قبل المستخدم):
   - إذا كانت YES: يجب أن يكون ردك مطمئناً وتؤكد للعميل أنه سيتم رفع طلب/تذكرة له لتنفيذ الإجراء المطلوب (مثل إرسال فني).
   - إذا كانت NO: قم بالإجابة على استفسار العميل مباشرة بناءً على السياق المتاح.
2. اكتب الرد باللهجة المصرية اللبقة والمحترفة.
3. التزم تماماً بالمعلومات المذكورة في السياق ولا تخترع أي أسعار أو معلومات غير موجودة.

السياق المتاح لمساعدة العميل:
{context}"""

    generation_user = f"""سؤال العميل: "{query}"
حالة طلب العميل (هل يتطلب إجراء/تذكرة من السيستم؟): {needs_action}

اكتب الرد الموجه للعميل بناءً على ما سبق:"""

    gen_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": generation_system},
            {"role": "user", "content": generation_user},
        ],
        max_tokens=500,
        temperature=0.3,
    )

    final_answer = gen_response.choices[0].message.content.strip()

    return {
        "answer": final_answer,
        "needs_action": needs_action,
        "cleaned_answer": final_answer,
        "sources": [res["source"] for res in retrieved_results],
    }


# ============================================================
# 7. RUN RAG PIPELINE  — copied verbatim
# ============================================================
def run_rag_pipeline_fn(query: str, model, index, all_chunks, metadata):
    """
    Full RAG pipeline (standalone function).
    Copied verbatim from the original script — only the global variable
    references (model, index, all_chunks, metadata) are passed as arguments
    so the function works inside the class without globals.
    """
    print(f"\n{'='*80}")
    print(f"User Query: {query}")

    route = route_query(query)

    if route == "out_of_scope":
        return {
            "answer": "آسف يا فندم، الموضوع ده خارج عن نطاق مساعد الدعم الفني بتاعنا. ممكن أساعدك بحاجة تانية؟",
            "needs_action": "NO",
            "sources": [],
        }

    if route == "ticket":
        return {
            "answer": "تمام يا فندم سيتم إنشاء تذكرة لمشكلتك وسيتم التعامل معها في أسرع وقت ممكن. هل تود أن أساعدك في شيء آخر؟",
            "needs_action": "YES",
            "sources": [],
        }

    if route == "chat":
        retrieved = retrieve(query, model, index, all_chunks, metadata)
        answer = generate_answer(query, retrieved)
        return answer


# ============================================================
# 8. TelecomRAG CLASS
#    Thin wrapper — builds the pipeline once, then exposes
#    run_rag_pipeline(query) for the FastAPI backend in main.py.
# ============================================================
class TelecomRAG:
    """
    Wraps the original pipeline into a reusable object.

    __init__  → loads docs → chunk_text() → create_embeddings() → build_faiss_index()
    run_rag_pipeline(query) → route_query() → retrieve() → generate_answer()
    """

    def __init__(self, data_path: str = DATA_PATH):
        self.data_path  = data_path
        self.all_chunks = []
        self.metadata   = []
        self.model      = None
        self.index      = None

        self._build()

    # ── mirrors the original __main__ block exactly ───────────────────────────
    def _build(self):

        # Load data
        for file in os.listdir(self.data_path):
            if file.endswith(".md"):
                with open(os.path.join(self.data_path, file), "r", encoding="utf-8") as f:
                    text = f.read()
                doc_chunks = chunk_text(text)           # <- original function
                for chunk in doc_chunks:
                    self.all_chunks.append(chunk)
                    self.metadata.append({"source": file})

        # Embeddings
        self.model, embeddings = create_embeddings(self.all_chunks)   # <- original function

        # Index
        self.index = build_faiss_index(embeddings)                    # <- original function

        print("\n=== System Ready! ===\n")

    # ── public interface for main.py ──────────────────────────────────────────
    def run_rag_pipeline(self, query: str) -> dict:
        """Delegates to run_rag_pipeline_fn() with the stored state."""
        return run_rag_pipeline_fn(
            query      = query,
            model      = self.model,
            index      = self.index,
            all_chunks = self.all_chunks,
            metadata   = self.metadata,
        )