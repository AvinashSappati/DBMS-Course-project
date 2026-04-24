import json
import os
import sqlparse
from tqdm import tqdm
from test_model import Text2SQLEngine

# --- Configuration ---
# Adjust these paths to point to your local Spider dataset files
DEV_JSON_PATH = "spider/dev.json"
TABLES_JSON_PATH = "spider/tables.json"
OUTPUT_PREDICTIONS = "predictions.txt"

def normalize_sql(sql):
    """
    Normalizes SQL for a baseline string comparison.
    Removes extra whitespace, standardizes case, and strips trailing semicolons.
    """
    if not sql:
        return ""
    # Use sqlparse (from your requirements) to format the query
    sql = sqlparse.format(sql, keyword_case='upper', strip_comments=True)
    return " ".join(sql.split()).strip(";").lower()

def evaluate():
    if not os.path.exists(DEV_JSON_PATH) or not os.path.exists(TABLES_JSON_PATH):
        print(f"Error: Could not find Spider dataset files.")
        print(f"Please ensure {DEV_JSON_PATH} and {TABLES_JSON_PATH} exist.")
        return

    print(f"Loading Spider development dataset from {DEV_JSON_PATH}...")
    with open(DEV_JSON_PATH, "r", encoding="utf-8") as f:
        dev_data = json.load(f)

    print(f"Initializing Text2SQLEngine with schemas from {TABLES_JSON_PATH}...")
    # This will boot up your T5 model and BGE retriever
    engine = Text2SQLEngine(TABLES_JSON_PATH)

    correct_count = 0
    total_count = len(dev_data)
    predictions = []

    print(f"Starting inference on {total_count} queries...")
    
    # tqdm provides a progress bar so you aren't guessing if the script froze
    for item in tqdm(dev_data, desc="Evaluating"):
        question = item["question"]
        db_id = item["db_id"]
        ground_truth_sql = item["query"]

        # 1. Generate prediction using your engine
        result = engine.generate(question, db_id)
        
        # Handle cases where the engine returns vague or validation failures
        predicted_sql = result.get("sql")
        if predicted_sql is None:
            predicted_sql = "SELECT 1" # Fallback to prevent official script from crashing
            
        # 2. Save exact string format required by official Spider evaluation
        predictions.append(predicted_sql.replace('\n', ' ') + "\n")

        # 3. Calculate baseline normalized string match
        norm_predicted = normalize_sql(predicted_sql)
        norm_truth = normalize_sql(ground_truth_sql)

        if norm_predicted == norm_truth:
            correct_count += 1

    # 4. Compute and report baseline accuracy
    accuracy = (correct_count / total_count) * 100

    print("\n" + "="*40)
    print("      EVALUATION COMPLETE")
    print("="*40)
    print(f"Total Queries Evaluated : {total_count}")
    print(f"Strict String Matches   : {correct_count}")
    print(f"Baseline Accuracy       : {accuracy:.2f}%")
    print("="*40)
    print("* Note: This is a strict string match. True accuracy (EM) will be higher.")

    # 5. Export predictions
    print(f"\nSaving raw predictions to '{OUTPUT_PREDICTIONS}'...")
    with open(OUTPUT_PREDICTIONS, "w", encoding="utf-8") as f:
        f.writelines(predictions)
        
    print("Done! To get your final official score, run the Yale Lily Spider evaluation script:")
    print(f"python evaluation.py --gold {DEV_JSON_PATH} --pred {OUTPUT_PREDICTIONS} --etype match --table {TABLES_JSON_PATH}")

if __name__ == "__main__":
    evaluate()