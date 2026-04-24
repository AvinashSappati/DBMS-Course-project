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
async def generate(schema_text: str = Form(...), question: str = Form(...)):
    global engine

    # We don't need to read/decode a file anymore! 
    # Just pass the raw text string directly to your parser.
    schema_json = parse_schema_text_to_json(schema_text)

    # Write straight to the root directory
    schema_path = "schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema_json, f)

    db_id = schema_json[0]["db_id"]

    # Load model onto GPU ONLY if it's the first time
    if engine is None:
        print("Booting up T5 and BGE models...")
        engine = Text2SQLEngine(schema_path)
    else:
        # Hot-swap the schema
        engine.schemas.update(load_schemas(schema_path))

    # Generate the SQL
    result = engine.generate(question, db_id)

    return result