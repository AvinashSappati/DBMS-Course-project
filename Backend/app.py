import gradio as gr
import json
from test_model import Text2SQLEngine
from parser import parse_schema_text_to_json

engine = None

def load_model():
    global engine
    if engine is None:
        print("Loading model...")
        engine = Text2SQLEngine("dummy.json")

def generate(file, question):
    load_model()

    # read uploaded file
    raw_text = file.read().decode("utf-8")

    # convert schema → json
    schema_json = parse_schema_text_to_json(raw_text)

    with open("temp.json", "w") as f:
        json.dump(schema_json, f)

    db_id = schema_json[0]["db_id"]

    result = engine.generate(question, db_id)

    return result.get("sql", str(result))


demo = gr.Interface(
    fn=generate,
    inputs=[
        gr.File(label="Upload Schema (.txt)"),
        gr.Textbox(label="Enter Question")
    ],
    outputs="text",
    title="Text → SQL Generator"
)

demo.launch()