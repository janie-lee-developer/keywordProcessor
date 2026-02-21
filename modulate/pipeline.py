import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["AIRIA_KEYWORD_KEY"]
API_URL = os.environ["AIRIA_KEYWORD_URL"]
HEADERS = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}


def run(record: dict) -> dict:
    print(f"\n[pipeline] Extracting keyword from utterance...")
    payload = json.dumps({"userInput": json.dumps(record), "asyncOutput": False})
    response = requests.post(API_URL, headers=HEADERS, data=payload)
    response.raise_for_status()

    result_str = response.json().get("result", "")
    print(f"[pipeline] Raw: {result_str[:300]}")

    try:
        data = json.loads(result_str)
        keyword = data.get("keyword", "")
        description = data.get("description", "")
        print(f"[pipeline] Keyword: {keyword}")
        return {"keyword": keyword, "description": description}
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[pipeline] Parse error: {e}")
        return {"keyword": "", "description": ""}
