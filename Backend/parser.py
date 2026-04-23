import re
import json

def parse_schema_text_to_json(raw_text, db_id="custom_db"):

    tables = []
    table_names = []
    column_names = [[-1, "*"]]
    column_types = ["text"]
    primary_keys = []
    foreign_keys = []

    table_blocks = re.findall(r'(\w+)\s*\((.*?)\)', raw_text, re.DOTALL)

    col_id = 1
    table_id_map = {}
    column_id_map = {}

    # Parse tables
    for tid, (table_name, cols_block) in enumerate(table_blocks):

        table_names.append(table_name)
        table_id_map[table_name] = tid

        cols = cols_block.split("\n")

        for col in cols:
            col = col.strip().replace(",", "")
            if not col:
                continue

            parts = col.split()

            col_name = parts[0]
            col_type = parts[1] if len(parts) > 1 else "TEXT"

            column_names.append([tid, col_name])
            column_types.append(col_type.lower())

            column_id_map[f"{table_name}.{col_name}"] = col_id

            # PRIMARY KEY
            if "PK" in col.upper():
                primary_keys.append(col_id)

            col_id += 1

    # Detect FOREIGN KEYS
    for table_name, cols_block in table_blocks:
        cols = cols_block.split("\n")

        for col in cols:
            col = col.strip().replace(",", "")
            if not col:
                continue

            parts = col.split()
            col_name = parts[0]

            if "FK" in col.upper():

                # heuristic: dept_id → Departments.dept_id
                ref_name = col_name.replace("_id", "")

                for t in table_names:
                    if t.lower().startswith(ref_name.lower()):

                        src = column_id_map[f"{table_name}.{col_name}"]
                        dst = column_id_map.get(f"{t}.{col_name}")

                        if dst:
                            foreign_keys.append([src, dst])

    # Final JSON
    result = [{
        "db_id": db_id,
        "table_names": table_names,
        "table_names_original": table_names,
        "column_names": column_names,
        "column_names_original": column_names,
        "column_types": column_types,
        "primary_keys": primary_keys,
        "foreign_keys": foreign_keys
    }]

    return result

def read_schema_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    return raw_text
