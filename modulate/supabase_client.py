import os
import sys
import json
import aiohttp
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


async def send_utterance(session: aiohttp.ClientSession, record: dict) -> None:
    url = f"{SUPABASE_URL}/rest/v1/voice_events"
    async with session.post(url, headers=HEADERS, json=record) as resp:
        if resp.status in (200, 201):
            print(f"[supabase] ✓ inserted utterance {record.get('utterance_uuid')}", file=sys.stderr)
        else:
            body = await resp.text()
            print(f"[supabase] ✗ utterance error {resp.status}: {body}", file=sys.stderr)


async def save_keywords(session: aiohttp.ClientSession, pipeline_result: dict) -> None:
    url = f"{SUPABASE_URL}/rest/v1/keyword"
    row = {"keyword": json.dumps(pipeline_result)}
    async with session.post(url, headers=HEADERS, json=row) as resp:
        if resp.status in (200, 201):
            print(f"[supabase] ✓ saved keyword dict", file=sys.stderr)
        else:
            body = await resp.text()
            print(f"[supabase] ✗ keyword error {resp.status}: {body}", file=sys.stderr)
