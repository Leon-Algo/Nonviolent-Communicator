# NVC Voice Agent via Agora ConvoAI

## Goal

Build a working NVC (Nonviolent Communication) voice coach agent in under 30 minutes using Agora Conversational AI Engine.

## Approach

Use the official Agora `agent-quickstart-python` quickstart as the baseline. Run it independently first to prove the voice pipeline works, then customize the agent persona for NVC coaching.

## Architecture

```
Browser (React frontend)
  | RTC + RTM
Agora ConvoAI Engine
  | ASR (Deepgram) -> LLM (OpenAI gpt-4o-mini) -> TTS (MiniMax)
Voice conversation
```

## Tech Stack

- **Baseline**: `agent-quickstart-python` (Python server + React frontend)
- **Package manager**: Bun
- **STT**: Deepgram nova-3 (default)
- **LLM**: OpenAI gpt-4o-mini (default)
- **TTS**: MiniMax speech_2_6_turbo (default)
- **No BYOK** — uses Agora's default pipeline, no vendor API keys needed

## NVC Coach Persona

The agent system prompt and greeting will be customized to act as an NVC practice partner:
- Guide users through OFNR (Observation-Feeling-Need-Request) expression
- Provide gentle feedback on communication patterns
- Offer practice scenarios for common workplace/personal communication challenges
- Respond in Chinese (matching the existing NVC product language)

## Execution Steps

1. Environment check — verify Bun, Python, Agora CLI
2. Agora CLI readiness — login, project selection, ConvoAI feature enablement
3. Clone official quickstart — `agent-quickstart-python`
4. Configure NVC coach persona — customize system prompt and greeting
5. Start and verify — first voice conversation end-to-end

## Success Criteria

- App loads at local URL
- User can start a conversation from the UI
- Agent joins the RTC channel
- User can speak to the agent and hear TTS back
- Agent responds with NVC-aware coaching behavior

## Future Integration

After the baseline works, potential paths include:
- Custom LLM backend connected to existing NVC analysis engine
- Integration into the existing NVC Communicator web app
- BYOK with higher-quality TTS/LLM providers
