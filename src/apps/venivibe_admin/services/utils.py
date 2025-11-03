import json
from pathlib import Path

def load_config(filename):
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config" / filename
    with open(config_path) as f:
        return json.load(f)

risk_cfg = load_config("risk_score_config.json")

if __name__ == "__main__":
    print(risk_cfg)
    import os
    from dotenv import load_dotenv
    load_dotenv()
    DEBUG = os.getenv("DEBUG")
    print(DEBUG)