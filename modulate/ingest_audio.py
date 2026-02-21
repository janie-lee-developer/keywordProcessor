"""
Zoom Audio → Modulate Velma-2 → Supabase + Airia keyword extraction.

Setup:
  1. brew install blackhole-2ch
  2. Zoom Settings → Audio → Speaker → Multi-Output Device (BlackHole + speakers)
  3. Copy .env.example to .env and fill in your keys

Run:
  python ingest_audio.py
  python ingest_audio.py --list-devices
  python ingest_audio.py --device 3
"""

import os
import argparse
import asyncio
import json
import queue
import struct
import sys
import time

import aiohttp
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

import pipeline as airia_pipeline
from supabase_client import send_utterance, save_keywords

load_dotenv()

API_URL = os.environ["VELMA_API_URL"]
API_KEY = os.environ["VELMA_API_KEY"]

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_MS = 100
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_MS / 1000)

HARM_SCORES = {
    "Angry": 0.95, "Contemptuous": 0.90, "Disgusted": 0.85,
    "Frustrated": 0.75, "Disappointed": 0.65,
    "Stressed": 0.55, "Anxious": 0.50, "Afraid": 0.45,
    "Sad": 0.35, "Ashamed": 0.35, "Concerned": 0.30,
    "Confused": 0.25, "Bored": 0.20, "Tired": 0.20,
    "Surprised": 0.15, "Neutral": 0.05,
    "Calm": 0.02, "Happy": 0.02, "Amused": 0.02,
    "Excited": 0.05, "Proud": 0.02, "Affectionate": 0.02,
    "Interested": 0.05, "Hopeful": 0.02, "Relieved": 0.02,
    "Confident": 0.05,
}


def make_wav_header(sample_rate=SAMPLE_RATE, channels=CHANNELS, sample_width=2):
    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width
    return (
        b"RIFF" + struct.pack("<I", 0xFFFFFFFF) +
        b"WAVE" +
        b"fmt " + struct.pack("<IHHIIHH",
            16, 1, channels, sample_rate, byte_rate, block_align, sample_width * 8) +
        b"data" + struct.pack("<I", 0xFFFFFFFF)
    )


def find_blackhole(preferred_index=None):
    if preferred_index is not None:
        return preferred_index
    for i, d in enumerate(sd.query_devices()):
        if "blackhole" in d["name"].lower() and d["max_input_channels"] > 0:
            return i
    return None


def list_devices():
    print("\nAvailable audio input devices:")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            print(f"  [{i}] {d['name']}")
    print()


async def run(device_index):
    audio_queue: queue.Queue[bytes] = queue.Queue()
    session_id = f"zoom-{int(time.time())}"

    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"[audio] {status}", file=sys.stderr)
        pcm = (indata[:, 0] * 32767).astype(np.int16)
        audio_queue.put(pcm.tobytes())
        volume = np.abs(indata).mean()
        bars = int(volume * 50)
        print(f"\r[mic] {'█' * bars:<20} {volume:.4f}", end="", flush=True, file=sys.stderr)

    ws_url = (
        f"{API_URL}"
        f"?api_key={API_KEY}"
        f"&speaker_diarization=true"
        f"&emotion_signal=true"
    )

    print(f"Connecting to Velma-2...", file=sys.stderr)
    print(f"Device [{device_index}]: {sd.query_devices(device_index)['name']}", file=sys.stderr)
    print(f"Session: {session_id}\n", file=sys.stderr)

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(ws_url) as ws:
            print("Connected. Listening to Zoom...\n", file=sys.stderr)

            async def send_audio():
                await ws.send_bytes(make_wav_header())
                while True:
                    try:
                        chunk = audio_queue.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.01)
                        continue
                    await ws.send_bytes(chunk)

            send_task = asyncio.create_task(send_audio())

            with sd.InputStream(
                device=device_index,
                channels=CHANNELS,
                samplerate=SAMPLE_RATE,
                blocksize=CHUNK_FRAMES,
                dtype="float32",
                callback=audio_callback,
            ):
                try:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)

                            if data.get("type") == "utterance":
                                u = data["utterance"]
                                emotion = u.get("emotion") or None
                                harm = HARM_SCORES.get(emotion, 0.05) if emotion else 0.05

                                record = {
                                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                    "session_id": session_id,
                                    "speaker": u["speaker"],
                                    "language": u.get("language"),
                                    "emotion": emotion,
                                    "harm_score": harm,
                                    "text": u["text"],
                                    "start_ms": u.get("start_ms"),
                                    "duration_ms": u.get("duration_ms"),
                                    "utterance_uuid": u.get("utterance_uuid"),
                                }

                                print(json.dumps(record), flush=True)
                                print(
                                    f"\n[{record['timestamp']}] Speaker {u['speaker']} | "
                                    f"emotion={emotion or '—':<15} harm={harm:.2f} | "
                                    f"{u['text']}\n",
                                    file=sys.stderr,
                                )

                                loop = asyncio.get_event_loop()
                                _, pipeline_result = await asyncio.gather(
                                    send_utterance(session, record),
                                    loop.run_in_executor(None, airia_pipeline.run, record),
                                )

                                if pipeline_result.get("keyword"):
                                    await save_keywords(session, pipeline_result)

                            elif data.get("type") == "error":
                                print(f"[error] {data.get('error')}", file=sys.stderr)
                                break

                            elif data.get("type") == "done":
                                print(f"\nSession done. Duration: {data.get('duration_ms')}ms", file=sys.stderr)
                                break

                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
                finally:
                    send_task.cancel()


def main():
    parser = argparse.ArgumentParser(description="Stream Zoom audio to Modulate Velma-2")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--device", type=int, default=None)
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    device_index = find_blackhole(args.device)
    if device_index is None:
        print("BlackHole not found. Run --list-devices to see options.")
        sys.exit(1)

    try:
        asyncio.run(run(device_index))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
