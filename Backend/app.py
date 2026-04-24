from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import json

from test_model import Text2SQLEngine, load_schemas
from parser import parse_schema_text_to_json

app = FastAPI()

# Crucial for allowing your Vercel frontend to talk to this Colab backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep the heavy model in memory so it doesn't reload on every click
engine = None

@app.get("/")
def home():
    return {"msg": "Backend running 🚀"}

@app.post("/generate")
async def generate(file: UploadFile = File(...), question: str = Form(...)):
    global engine

    # 1. Read and parse the uploaded text file
    content = await file.read()
    raw_text = content.decode("utf-8")
    schema_json = parse_schema_text_to_json(raw_text)

    # 2. Write straight to the root directory (No temp folder clutter!)
    schema_path = "schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema_json, f)

    db_id = schema_json[0]["db_id"]

    # 3. Load model onto GPU ONLY if it's the first time
    if engine is None:
        print("Booting up T5 and BGE models...")
        engine = Text2SQLEngine(schema_path)
    else:
        # SDE Move: Instantly update the schema without reloading the AI models
        engine.schemas.update(load_schemas(schema_path))

    # 4. Generate the SQL
    result = engine.generate(question, db_id)

    return result