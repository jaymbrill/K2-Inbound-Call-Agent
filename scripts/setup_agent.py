"""
Run this script once to create your ElevenLabs Conversational AI agent.
After it completes, copy the printed ELEVENLABS_AGENT_ID into your .env file.

Usage:
    python scripts/setup_agent.py
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_LLM = os.getenv("ELEVENLABS_LLM", "claude-3-5-sonnet")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

BASE_SYSTEM_PROMPT = """You are K2, a warm and engaging personal voice assistant. \
You are having a real phone conversation — keep responses concise and natural. \
This is voice, not text: no lists, bullet points, or long paragraphs. \
Listen actively and refer back to what the caller shares before moving on."""

AGENT_CONFIG = {
    "name": "K2 Inbound Call Agent",
    "conversation_config": {
        "agent": {
            "prompt": {
                "prompt": BASE_SYSTEM_PROMPT,
                "llm": ELEVENLABS_LLM,
                "temperature": 0.7,
            },
            "first_message": "Hello! Thanks for calling.",
            "language": "en",
        },
        "tts": {
            "model_id": "eleven_turbo_v2_5",
            "voice_id": ELEVENLABS_VOICE_ID,
            "optimize_streaming_latency": 3,
        },
        "asr": {
            "quality": "high",
            "provider": "elevenlabs",
        },
        "turn": {
            "turn_timeout": 20,
            "silence_end_call_timeout": 30,
        },
    },
}


def create_agent() -> str:
    if not ELEVENLABS_API_KEY:
        sys.exit("ERROR: ELEVENLABS_API_KEY is not set. Add it to your .env file.")

    print(f"Creating ElevenLabs agent with LLM: {ELEVENLABS_LLM}")

    with httpx.Client() as client:
        resp = client.post(
            "https://api.elevenlabs.io/v1/convai/agents",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json=AGENT_CONFIG,
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()

    agent_id = data.get("agent_id") or data.get("id", "")
    if not agent_id:
        sys.exit(f"ERROR: Unexpected response — no agent_id found:\n{data}")

    print(f"\nAgent created successfully!")
    print(f"\nAdd this to your .env file:\n  ELEVENLABS_AGENT_ID={agent_id}")
    return agent_id


def get_existing_agents():
    with httpx.Client() as client:
        resp = client.get(
            "https://api.elevenlabs.io/v1/convai/agents",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            timeout=10.0,
        )
        resp.raise_for_status()
        agents = resp.json().get("agents", [])

    if not agents:
        print("No existing agents found.")
        return

    print("\nExisting agents:")
    for agent in agents:
        print(f"  {agent.get('name', 'Unnamed')} — ID: {agent.get('agent_id', agent.get('id', '?'))}")


if __name__ == "__main__":
    if "--list" in sys.argv:
        get_existing_agents()
    else:
        create_agent()
