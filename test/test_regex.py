import sys
import os
import re
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules_ai import parsing_regex_fields

patterns = {
    "TASKCARD": r"TASKCARD\s+([A-Z]{2}-\d{3}-\d{2}-\d(?:-\d+)?\s*\(\d+\))",
    "WORK_ORDER": r"ITEM-1(WO\s*\d{7})",  # Captura desde ITEM-1 hasta fin de WO
    "LOCATION": r"(?:^|:|\s)((?:AFT\s+CARGO|R/H\s+WING|L/H\s+WING|WINGS?))",
    "PANEL_CODE": r"FIN\s+(\d{3}[A-Z]{2})(?=\s|$)",
    "part_numbers": r"P/N\s*[:]?\s*([A-Z]\d{7,15})(?=\s|$)",
    "amm_tasks": r"AMM\s*TASK\s*([\d\-A-Z]+)(?=\s|$|\.)",
    "amm_revisions": {
        "task": r"AMM\s*([\d\-]+)\s",
        "revision": r"(?:REV\.?\s*(\d+)|PB(\d+))"
    },
    "actions": {
        "send_to_workshop": r"SEND\s*TO\s*WORKSHOP",
        "damage_out_of_limits": r"DAMAGES?\s*OUT\s*OF?\s*LIMITS",
        "supply_new_panel": r"(?:SUPPLY|SUPPLIED|INSTALL)\s*NEW\s*PANEL"
    }
}

def extract_data(text):
    result = {}
    
    # Extracción directa
    for field, pattern in patterns.items():
        if field in ["part_numbers", "amm_tasks"]:
            result[field] = re.findall(pattern, text, re.IGNORECASE)
        elif field == "TASKCARD":
            match = re.search(pattern, text)
            result[field] = match.group(1) if match else None
        elif field == "WORK_ORDER":
            match = re.search(pattern, text)
            if match:
                # Limpieza de espacios en WO
                result[field] = re.sub(r"\s+", "", match.group(1))
        elif field == "LOCATION":
            match = re.search(pattern, text, re.IGNORECASE)
            result[field] = match.group(1).strip() if match else None
        elif field == "PANEL_CODE":
            match = re.search(pattern, text)
            result[field] = match.group(1) if match else None
    
    # Manejo especial para revisiones
    result["amm_revisions"] = []
    task_matches = re.finditer(patterns["amm_revisions"]["task"], text)
    for task_match in task_matches:
        task = task_match.group(1)
        rev_text = text[task_match.end():task_match.end()+20]
        rev_match = re.search(patterns["amm_revisions"]["revision"], rev_text)
        if rev_match:
            revision = rev_match.group(1) or f"PB{rev_match.group(2)}"
            result["amm_revisions"].append({"task": task, "revision": revision})
    
    # Banderas de acciones
    result["actions"] = {}
    for action, pattern in patterns["actions"].items():
        result["actions"][action] = bool(re.search(pattern, text, re.IGNORECASE))
    
    return result


if __name__ == "__main__":
    findings_file = r"C:\Users\CristianEscudero\Documents\projects\eda\data\Findings_PP_compactado.xlsx"
    df = pd.read_excel(findings_file, sheet_name='Sheet1')
    descriptions = df['Description'].tolist()
    for desc in descriptions:
        print(f"{desc}\n")
        print(extract_data(desc))