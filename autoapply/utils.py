import json
import yaml

def read(file: str) -> dict | str:
    with open(file, "r") as f:
        if file.endswith(".json"):
            return json.load(f)
        elif file.endswith(".yaml"):
            return yaml.safe_load(f)
        else:
            return f.readlines()

