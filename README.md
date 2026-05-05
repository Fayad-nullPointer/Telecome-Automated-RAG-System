# 📡 NileTel Telecom RAG System

An intelligent, Arabic-native AI support assistant and ticket management system for a fictitious telecom company (NileTel). It uses Retrieval-Augmented Generation (RAG) to accurately answer customer queries based on company policies, FAQs, and technical guides. Furthermore, it automatically classifies whether a query requires live action (like dispatching a technician or opening a ticket) and integrates with n8n to automate the creation of tickets and notify customers via email.

---

## ✨ Features

- **Arabic Native RAG System:** Uses SentenceTransformers (`multilingual-e5-small`) and Groq (`llama-3.3-70b-versatile`) to provide highly accurate, contextual answers in Egyptian Arabic.
- **Smart Query Routing:** Dynamically categorizes incoming queries as either technical support/chat, explicit ticket requests, or completely out-of-scope topics.
- **Automated Ticket Classification:** Evaluates whether a customer's query needs administrative action (e.g., "My internet is down, I need a technician") and flags it accordingly (`needs_action = YES/NO`).
- **N8N Automation & Webhooks:** Integrates seamlessly with n8n workflows to automatically append ticket entries to a Google Sheet and send confirmation emails to the user.
- **Microservices Architecture:** 
  - A core RAG engine.
  - A FastAPI backend for serving the AI.
  - A Customer-facing Streamlit app.
  - An Employee-facing Streamlit dashboard for resolving tickets.

---

## 🏗️ Architecture

![Automated Pipeline](Image/Pasted%20image.png)

1. **RAG Engine (`rag_core.py`)**
   - **Data Ingestion:** Reads Markdown files from the `/data` directory (policies, FAQs, technical guides).
   - **Vector Database:** Chunks text and generates embeddings, storing them in a local **FAISS** index for ultra-fast retrieval.
   - **LLM Inferencing:** Uses the Groq API for both routing and text generation, grounding responses purely on retrieved context.

2. **Backend API (`mains2.py`)**
   - Built with **FastAPI**.
   - Loads the FAISS index and Embedding models once on startup.
   - Exposes a RESTful `/ask` POST endpoint tailored for the frontend client.

3. **Customer Support Assistant (`streams2.py`)**
   - Built with **Streamlit** (configured with Right-to-Left Arabic UI).
   - Allows users to type queries and input their Email and Phone number.
   - Hits the FastAPI backend to retrieve answers.
   - If `needs_action == YES`, it triggers an **n8n Webhook** payload.

4. **Employee Dashboard (`employee_app.py`)**
   - Built with **Streamlit**.
   - Pulls active open tickets dynamically from a Google Sheet.
   - Allows telecom employers to filter, view, and mark tickets as "Closed", "In Progress", or "Escalated".

5. **n8n Workflow**
   - Captures webhooks from the Customer App.
   - Appends a new row to a Google Sheet database.
   - Triggers an automated Gmail notification to the user assuring them their ticket was opened.

---

## 🚀 Setup & Installation

### 1. Requirements

- Python 3.9+
- A [Groq](https://wow.groq.com/) API key.
- An [n8n](https://n8n.io/) instance (Cloud or Self-hosted) with active webhooks.
- A configured Google Sheet with public CSV export configurations.

### 2. Install Dependencies

```bash
pip install fastapi uvicorn streamlit pandas requests faiss-cpu sentence-transformers groq python-dotenv numpy
```

### 3. Environment Variables

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Configure Data path and Webhooks

- In `rag_core.py`, ensure `DATA_PATH` points to your `data/` folder containing the markdown files.
- In `streams2.py`, ensure the `N8N_WEBHOOK_URL` points to your active n8n workflow listener.
- In `streams2.py` and `employee_app.py`, update the `SHEET_URL` parameter to match your Google Sheet's export ID.

---

## 🛠️ Usage / Running the Application

You need to run the services in sequence across different terminal windows.

### Step 1: Start the Backend (FastAPI + RAG Core)
This will ingest the documents, build the FAISS vector database in memory, and start the API port.
```bash
python mains2.py
```
*API will run on `http://localhost:8000`*

### Step 2: Start the Customer Chatbot (Streamlit)
```bash
streamlit run streams2.py
```
*Runs on `http://localhost:8501`. Customers will interact with this interface.*

### Step 3: Start the Employee Dashboard (Streamlit)
```bash
streamlit run employee_app.py
```
*Runs on `http://localhost:8502` (if 8501 is occupied). Technical support staff will use this to manage tickets.*

---

## 📚 Data Structure

The system relies on reading Markdown files to learn about Telecom Policies. Examples of included data from the `data/` directory:
- `5g_throttling_troubleshooting.md`
- `billing_dispute_procedure.md`
- `fiber_activation_policy_2026.md`
- `ntra_regulations_summary.md`

Make sure all rules, policies, and offers remain up-to-date in this folder. When files are updated, you must restart the FastAPI backend to rebuild the FAISS embeddings.

---

## 💻 Tech Stack

- **LLM API Provider:** Groq
- **Models:** LLaMA-3.3-70b-versatile (Generation & Routing), intfloat/multilingual-e5-small (Embeddings)
- **Vector DB:** FAISS
- **Backend:** FastAPI, Pydantic
- **Frontend / Dashboards:** Streamlit, Pandas
- **Automation / Integration:** n8n, Google Sheets, Gmail API