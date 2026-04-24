from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import json

from test_model import Text2SQLEngine, load_schemas
from parser import parse_schema_text_to_json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Heavy model in memory 
engine = None

@app.get("/")
def home():
    return {"msg": "Backend running 🚀"}

@app.post("/generate")
async def generate(schema_text: str = Form(...), question: str = Form(...)):
    
    global engine
    schema_json = parse_schema_text_to_json(schema_text)

    # Write straight to the root directory
    schema_path = "schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema_json, f)

    db_id = schema_json[0]["db_id"]

    # Loading model into GPU 
    if engine is None:
        print("Booting up T5 and BGE models...")
        engine = Text2SQLEngine(schema_path)
    else:
        # Hot-swap the schema
        engine.schemas.update(load_schemas(schema_path))
        
    result = engine.generate(question, db_id)

    return result
