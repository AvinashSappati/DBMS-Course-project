from fastapi import FastAPI, UploadFile, Form
import json
from test_model import Text2SQLEngine
from parser import parse_schema_text_to_json

app = FastAPI()

engine = None

@app.on_event("startup")
def load_model():
    global engine
    print("Loading model...")
    engine = Text2SQLEngine("dummy.json")

@app.get("/")
def home():
    return {"msg": "Backend running"}

@app.post("/generate")
async def generate(file: UploadFile, question: str = Form(...)):
    global engine

    raw_text = await file.read()
    raw_text = raw_text.decode("utf-8")

    schema_json = parse_schema_text_to_json(raw_text)

    with open("temp.json", "w") as f:
        json.dump(schema_json, f)

    db_id = schema_json[0]["db_id"]

    result = engine.generate(question, db_id)

    return result