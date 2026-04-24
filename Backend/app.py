from fastapi import FastAPI, UploadFile, File, Form
import json

from test_model import Text2SQLEngine
from parser import parse_schema_text_to_json  # your parser
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

engine = None

def load_model():
    global engine
    engine = Text2SQLEngine("dummy.json")  # will replace dynamically

@app.get("/")
def home():
    return {"msg": "Text2SQL API running 🚀"}


@app.post("/generate")
async def generate(file: UploadFile = File(...), question: str = Form(...)):
    
    # read schema.txt
    content = await file.read()
    raw_text = content.decode("utf-8")
    
    # convert to JSON
    schema_json = parse_schema_text_to_json(raw_text)
    
    with open("temp.json", "w") as f:
        json.dump(schema_json, f)
    
    db_id = schema_json[0]["db_id"]
    
    # load engine dynamically
    engine = Text2SQLEngine("temp.json")
    
    result = engine.generate(question, db_id)
    
    return result

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)