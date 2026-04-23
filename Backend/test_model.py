"""### TRANSFORMER And etc.."""
import re
import json
import numpy as np
import torch
import sqlparse,argparse

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import T5ForConditionalGeneration, T5Tokenizer

# Configuration
MODEL_NAME       = "yashwantk05/t5-finetuned"
BGE_MODEL_NAME   = "BAAI/bge-base-en-v1.5"
MAX_INPUT_LENGTH = 1024
MAX_NEW_TOKENS   = 256
NUM_BEAMS        = 2

# Retrieval thresholds
SIMILARITY_THRESHOLD  = 0.45   # min table score to include
VAGUE_THRESHOLD       = 0.30   # below this → ask for clarification
MAX_TABLES_FALLBACK   = 5
TOP_K_COLUMNS         = 12

# Schema loader
def load_schemas(tables_path: str) -> dict:
    with open(tables_path) as f:
        raw = json.load(f)

    schemas = {}
    for db in raw:
        db_id   = db["db_id"]
        t_names = db["table_names_original"]
        c_names = db["column_names_original"]
        c_types = db["column_types"]
        pk_ids  = set(db.get("primary_keys", []))
        fk_pairs= db.get("foreign_keys", [])

        col_lookup = {}
        for cid, (tid, cname) in enumerate(c_names):
            if tid == -1:
                continue
            col_lookup[cid] = (t_names[tid], cname)

        # Crucial for JOIN Operations
        fk_map = {}
        for (src_cid, dst_cid) in fk_pairs:
            if dst_cid in col_lookup:
                ref_table, ref_col = col_lookup[dst_cid]
                fk_map[src_cid] = f"{ref_table}.{ref_col}"

        columns = {t: [] for t in t_names}
        pks     = {t: set() for t in t_names}
        fks     = {t: {} for t in t_names}

        for cid, (tid, cname) in enumerate(c_names):
            if tid == -1:
                continue
            tname = t_names[tid]
            ctype = c_types[cid]
            columns[tname].append((cname, ctype.upper()))
            if cid in pk_ids:
                pks[tname].add(cname)
            if cid in fk_map:
                fks[tname][cname] = fk_map[cid]

        schemas[db_id] = dict(tables=t_names, columns=columns, pks=pks, fks=fks)

    return schemas

# Schema Representations

# Understanding schema semantically .
def build_table_text(table_name, columns, pks, fks) -> str:
    parts = []
    for col_name, col_type in columns:
        tags = []
        if col_name in pks:
            tags.append("PK")
        if col_name in fks:
            tags.append(f"FK→{fks[col_name]}")
        tags.append(col_type)
        parts.append(f"{col_name} ({' '.join(tags)})")
    return f"{table_name}: {', '.join(parts)}"

# For Embedding similarity
def build_column_texts(schema) -> tuple:
    texts, labels = [], []
    for tname in schema["tables"]:
        pks = schema["pks"][tname]
        fks = schema["fks"][tname]
        for col_name, col_type in schema["columns"][tname]:
            tags = []
            if col_name in pks:
                tags.append("PK")
            if col_name in fks:
                tags.append(f"FK→{fks[col_name]}")
            tags.append(col_type)
            texts.append(f"{tname}.{col_name} ({' '.join(tags)})")
            labels.append(f"{tname}.{col_name}")
    return texts, labels

# BGE Retriever
class SchemaRetriever:
    def __init__(self, model_name: str = BGE_MODEL_NAME):
        print(f"Loading BGE model: {model_name} ...")
        self.model = SentenceTransformer(model_name)
        self.model.eval()

    def retrieve(
        self,
        question: str,
        schema: dict,
        threshold: float = SIMILARITY_THRESHOLD,
        max_tables: int  = MAX_TABLES_FALLBACK,
        top_k_cols: int  = TOP_K_COLUMNS,
    ) -> tuple[str, float]:
        col_texts, col_labels = build_column_texts(schema)
        if not col_texts:
            return "", 0.0

        q_emb   = self.model.encode([question], normalize_embeddings=True)
        col_emb = self.model.encode(col_texts,  normalize_embeddings=True)
        col_scores = cosine_similarity(q_emb, col_emb)[0] # finding relevant columns only

        k = min(top_k_cols, len(col_texts))
        top_col_idx = col_scores.argsort()[-k:][::-1]
        needed_tables = {col_labels[i].split(".")[0] for i in top_col_idx}

        table_texts = [
            build_table_text(t, schema["columns"][t], schema["pks"][t], schema["fks"][t])
            for t in schema["tables"]
        ]
        tbl_emb    = self.model.encode(table_texts, normalize_embeddings=True)
        tbl_scores = cosine_similarity(q_emb, tbl_emb)[0]

        max_score = float(tbl_scores.max())

        dynamic_tables = {
            schema["tables"][i]
            for i, s in enumerate(tbl_scores)
            if s >= threshold
        }
        if not dynamic_tables:
            dynamic_tables = {schema["tables"][tbl_scores.argmax()]}

        dynamic_tables  = set(list(dynamic_tables)[:max_tables])
        selected_tables = set(list(needed_tables | dynamic_tables)[:max_tables])

        create_stmts = []
        for tname in schema["tables"]:
            if tname not in selected_tables:
                continue
            pks  = schema["pks"][tname]
            fks  = schema["fks"][tname]
            cols = schema["columns"][tname]
            col_defs = []
            for col_name, col_type in cols:
                constraint = ""
                if col_name in pks:
                    constraint += " PRIMARY KEY"
                if col_name in fks:
                    constraint += f" REFERENCES {fks[col_name]}"
                col_defs.append(f"  {col_name} {col_type}{constraint}")
            stmt = f"CREATE TABLE {tname} (\n" + ",\n".join(col_defs) + "\n);"
            create_stmts.append(stmt)

        return "\n".join(create_stmts), max_score

# Prompt Builder
def build_prompt(question: str, schema_str: str) -> str:
    return f"translate English to SQL: {question} schema: {schema_str}"


# SQL Validator
def validate_sql(sql: str, schema: dict) -> tuple[bool, list[str]]:

    errors = []

    # Level 1: Syntax — sqlparse can parse it without errors
    try:
        parsed = sqlparse.parse(sql)
        if not parsed or not parsed[0].tokens:
            errors.append("Syntax error: could not parse the generated SQL.")
            return False, errors
    except Exception as e:
        errors.append(f"Syntax error: {e}")
        return False, errors

    #  Level 2: Semantic — all table/column names exist in schema
    all_tables  = {t.lower() for t in schema["tables"]}
    all_columns = set()
    for tname in schema["tables"]:
        for col_name, _ in schema["columns"][tname]:
            all_columns.add(col_name.lower())
            all_columns.add(f"{tname.lower()}.{col_name.lower()}")

    sql_upper = sql.upper()

    # Extract table names after FROM / JOIN
    table_pattern = re.findall(
        r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE
    )
    for t in table_pattern:
        if t.lower() not in all_tables:
            errors.append(f"Semantic error: table '{t}' does not exist in the schema.")

    if errors:
        return False, errors

    return True, []

# Inference engine
class Text2SQLEngine:

    def __init__(self, tables_path: str):

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Device: {self.device}")

        print("Loading schemas ...")
        self.schemas   = load_schemas(tables_path)
        self.retriever = SchemaRetriever()
        self.retriever.model.to(self.device)

        print(f"Loading T5 model: {MODEL_NAME} ...")
        self.tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)
        self.model     = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)
        self.model.to(self.device)
        self.model.eval()

    # ENTRY POINT
    def generate(self, question: str, db_id: str) -> dict:
        """
        Returns a dictIonary with:
            status      : "ok" | "vague" | "invalid_db" | "validation_failed"
            sql         : generated SQL string (if status == "ok")
            message     : human-readable message
            confidence  : BGE similarity score
            warnings    : list of validation warnings (if any)
        """

        # Checking if db_id exists
        if db_id not in self.schemas:
            available = list(self.schemas.keys())[:10]
            return {
                "status":  "invalid_db",
                "sql":     None,
                "message": f"Database '{db_id}' not found.\nAvailable (first 10): {available}",
                "confidence": 0.0,
                "warnings": [],
            }

        schema = self.schemas[db_id]

        # BGE retrieval + confidence check
        schema_str, confidence = self.retriever.retrieve(question, schema)

        if confidence < VAGUE_THRESHOLD:
            table_list = ", ".join(schema["tables"])
            return {
                "status":  "vague",
                "sql":     None,
                "message": (
                    f"Your question didn't clearly match anything in the '{db_id}' database "
                    f"(confidence: {confidence:.2f}).\n"
                    f"Could you be more specific?\n\n"
                    f"Available tables: {table_list}\n\n"
                    f"Example: instead of 'show me data', try 'list all singers with age above 30'."
                ),
                "confidence": confidence,
                "warnings": [],
            }

        # Building prompt and generating SQL
        prompt = build_prompt(question, schema_str)

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=MAX_INPUT_LENGTH,
            truncation=True,
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                num_beams=NUM_BEAMS,
                early_stopping=True,
            )

        sql = self.tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()

        # Validate generated SQL
        is_valid, errors = validate_sql(sql, schema)

        if not is_valid:
            return {
                "status":   "validation_failed",
                "sql":      sql,
                "message":  "SQL was generated but failed validation. Use with caution.",
                "confidence": confidence,
                "warnings": errors,
            }

        return {
            "status":     "ok",
            "sql":        sql,
            "message":    "Query generated successfully.",
            "confidence": confidence,
            "warnings":   [],
        }
