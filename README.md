# K2 Inbound Call Agent

A personal voice bot for inbound phone calls. When someone calls your Twilio number, the bot greets them with a personalized comment or joke based on who they are, then guides them through a configurable conversation.

**Stack:** Twilio (telephony) · ElevenLabs Conversational AI (voice + STT + LLM) · FastAPI

---

## How It Works

```
Caller dials your Twilio number
       │
       ▼
Twilio POSTs to /incoming-call
       │
       ▼
Server looks up caller by phone number
Builds personalized greeting + system prompt
Calls ElevenLabs register_call API
       │
       ▼
ElevenLabs returns TwiML → server forwards to Twilio
       │
       ▼
Twilio streams audio directly to ElevenLabs
       │
       ▼
ElevenLabs runs the conversation using your agent config
```

---

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url>
cd K2-Inbound-Call-Agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Fill in `.env`

| Variable | Where to find it |
|---|---|
| `ELEVENLABS_API_KEY` | [ElevenLabs dashboard](https://elevenlabs.io/app) → Profile → API Keys |
| `TWILIO_ACCOUNT_SID` | [Twilio Console](https://console.twilio.com) → Dashboard |
| `TWILIO_AUTH_TOKEN` | Same page |
| `TWILIO_PHONE_NUMBER` | Twilio → Phone Numbers (E.164 format: `+1XXXXXXXXXX`) |
| `SERVER_URL` | Your public URL (see step 4) |

Leave `ELEVENLABS_AGENT_ID` blank for now.

### 3. Create the ElevenLabs agent

```bash
python scripts/setup_agent.py
```

Copy the printed agent ID into `.env`:
```
ELEVENLABS_AGENT_ID=agent_...
```

> **Note on LLM:** The agent defaults to `claude-3-5-sonnet`. To use Claude, enable it in your ElevenLabs workspace settings. Alternatively, set `ELEVENLABS_LLM=gpt-4o` in `.env`.

### 4. Expose your server publicly

For local development, use [ngrok](https://ngrok.com):

```bash
ngrok http 8000
```

Copy the `https://...ngrok.io` URL into `.env` as `SERVER_URL`.

For production, deploy to Railway, Fly.io, or any HTTPS server.

### 5. Configure Twilio

1. Go to [Twilio Console](https://console.twilio.com) → Phone Numbers → your number
2. Under **Voice & Fax → "A call comes in"**, set:
   - **Webhook:** `POST https://your-domain.com/incoming-call`
3. Save

### 6. Run

```bash
python main.py
```

Call your Twilio number — the bot answers!

---

## Customizing Callers

Edit `data/callers.json`. Keys are E.164 phone numbers:

```json
{
  "+15551234567": {
    "phone_number": "+15551234567",
    "name": "Jay",
    "nickname": "J",
    "notes": "Owner. Loves tech and coffee.",
    "joke": "Why do programmers prefer dark mode? Because light attracts bugs!",
    "call_count": 0,
    "is_known": true
  }
}
```

| Field | Description |
|---|---|
| `name` | Full name — used in greetings and system prompt |
| `nickname` | Short name used in the spoken greeting (optional) |
| `notes` | Free-form context fed into the agent's system prompt |
| `joke` | Personalized joke told at the start of every call |
| `call_count` | Auto-incremented — ordinal greeting on repeat calls |
| `is_known` | `true` = personalized greeting; `false` = ask who's calling |

Unknown callers (not in the database) get a warm default greeting and are asked for their name.

---

## Customizing the Conversation

Edit `data/questions.yaml`:

```yaml
intro_prompt: |
  After your opening greeting, guide the conversation naturally through the questions.
  Respond warmly before transitioning to each question.

questions:
  - id: checkin
    text: "How have you been lately?"
    variable_name: checkin
    required: true

  - id: projects
    text: "Any exciting projects or plans?"
    variable_name: projects
    required: false
```

The agent works through questions conversationally, not robotically. If a caller volunteers information that answers a later question, the agent acknowledges it and moves on naturally.

---

## Architecture Details

### Primary flow — `POST /incoming-call`
Calls ElevenLabs `register_call` API with a personalized `first_message` and `system_prompt` override. ElevenLabs returns TwiML; Twilio connects audio directly to ElevenLabs (no proxy hop through our server). Lowest latency.

### Fallback flow — `POST /incoming-call/proxy`
If the `register_call` API isn't available, the server returns TwiML pointing Twilio to our `/media-stream` WebSocket. The server proxies audio between Twilio and ElevenLabs and injects a `contextual_update` message with caller info.

Configure Twilio to use `/incoming-call/proxy` if the primary endpoint fails.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ELEVENLABS_API_KEY` | yes | — | ElevenLabs API key |
| `ELEVENLABS_AGENT_ID` | yes | — | Agent ID from setup script |
| `ELEVENLABS_LLM` | no | `claude-3-5-sonnet` | LLM for the agent |
| `ELEVENLABS_VOICE_ID` | no | Sarah | ElevenLabs voice ID |
| `TWILIO_ACCOUNT_SID` | yes | — | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | yes | — | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | yes | — | Your Twilio number (E.164) |
| `SERVER_URL` | yes | localhost | Public HTTPS URL of this server |
| `VALIDATE_TWILIO_SIGNATURE` | no | `true` | Set `false` for local dev without ngrok |
| `LOG_LEVEL` | no | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Health Check

```bash
curl https://your-domain.com/health
```

Returns `{"status": "ok", "agent_id": "agent_..."}`.
