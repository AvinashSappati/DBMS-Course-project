from fastapi import FastAPI, UploadFile, File, Form
import json
import os

from test_model import Text2SQLEngine
from parser import parse_schema_text_to_json

app = FastAPI()

@app.get("/")
def home():
    return {"msg": "Backend running 🚀"}


@app.post("/generate")
async def generate(file: UploadFile = File(...), question: str = Form(...)):

    content = await file.read()
    raw_text = content.decode("utf-8")

    schema_json = parse_schema_text_to_json(raw_text)

    os.makedirs("temp", exist_ok=True)

    temp_path = "temp/schema.json"
    with open(temp_path, "w") as f:
        json.dump(schema_json, f)

    db_id = schema_json[0]["db_id"]

    engine = Text2SQLEngine(temp_path)

    result = engine.generate(question, db_id)

    return result