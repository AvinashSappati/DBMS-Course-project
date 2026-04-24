# Text-to-SQL Engine: Natural Language to Database Queries
**Course Project: Database Management Systems** 

## 1. Introduction & Overview
This project bridges the gap between natural language and database execution. It is a full-stack AI application that translates plain English queries into valid SQL commands based on dynamic, user-provided database schemas. 
The core intelligence is powered by a **T5-base** model, fully fine-tuned on the Spider dataset to understand complex table relationships, JOIN operations, and nested queries. 

## 2. Spider Dataset & Model Testing
The model was rigorously tested against the **Spider Dataset**, a large-scale complex and cross-domain semantic parsing and text-to-SQL dataset.
* **Fine-Tuning:** The `T5-base` model was fine-tuned to map natural language questions directly to SQL logical forms.
* **Retrieval-Augmented Generation (RAG):** Utilizes `BAAI/bge-base-en-v1.5` sentence embeddings to filter and retrieve the most relevant tables and columns before generation, preventing context overflow.
* **Testing Results:** *(Achieved an execution accuracy of 8.22% on the Spider validation split by matching 85 out of 1034 queries having exact match ).*

## 3. Input Parsing & Core Logic
The system is designed to be highly modular and dynamic. It does not hardcode databases.
* **Schema Parsing (`parser.py`):** Automatically reads raw text schemas (DDL), extracts table structures, identifies Primary Keys (PKs), and detects Foreign Key (FK) relationships.
* **Inference Engine (`test_model.py`):** The central hub that loads the schemas, runs the BGE semantic similarity checks, builds the prompt, and generates the SQL sequence using the T5 model on a GPU.

## 4. Multi-Database Validation & Results
To ensure robustness, the engine includes a multi-tiered validation system before returning results:
1. **Syntax Validation:** Uses `sqlparse` to guarantee the generated query is syntactically valid SQL.
2. **Semantic Validation:** Cross-references the generated SQL against the parsed schema to ensure hallucinated tables or columns are caught and flagged.
* **Results:** Successfully tested across multiple distinct database environments (e.g., University schemas, Employee databases) with dynamic hot-swapping, requiring zero model retraining between databases. 

## 5. Deployment & Live Testing
The architecture is split to optimize for heavy ML processing while providing a seamless user experience.

* **Frontend (Vercel):** A responsive, glassmorphism UI built with vanilla HTML/JS/CSS, securely deployed on Vercel. 
* **Backend (Google Colab GPU):** A robust FastAPI REST server running on a free Colab T4 GPU, tunneled to the public web via `localtunnel`.

### How to Test the Live Application

**For the Evaluator/Professor:**
1. Open the Colab Notebook linked here: `[https://colab.research.google.com/drive/1SJP4zAQFyqjMG44tkCYgnp1FN9eIIlG0?usp=sharing]`
2. Run the three setup cells to launch the backend and generate the public URL and enter Localtunnel IP password.
3. Make that generated API_URL into javascript file and commit into Github.
4. Visit the live frontend here: `[https://dbms-course-project-blue.vercel.app/]`
5. Paste a database schema (e.g., `Students(id INT PK, name VARCHAR)`) into the text box.
6. Enter a natural language question and click **Generate SQL**.
