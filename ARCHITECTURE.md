# OSMIUMCORE — Architecture Specification & System Design

## 1. Executive Summary & Vision
OsmiumCore is an open-source, production-grade, modular, voice-first AI assistant ecosystem built with a modular clean architecture. It decouples voice transport from business logic, allowing seamless real-time interaction across Desktop and Mobile clients.



### Core Architecture Pillars
- **Sub-Second Latency:** Speech-to-Speech (S2S) processing targeting <800ms full round-trip.
- **Transport & Control Decoupling:** WebRTC (LiveKit) handles real-time audio transport, while REST/HTTP (FastAPI) handles metadata, system controls, and token authentication.
- **Dual Engine Core:** Dynamic switching between Cloud (Gemini Live API) and Local (Whisper + Ollama + TTS) execution pipelines.
- **Zero-Trust Client Access:** Short-lived JWTs scoped to specific rooms and identities.

---

## 2. High-Level System Design (HLD)

### 2.1 System Context & Boundaries
```text
┌─────────────────┐       ┌──────────────────┐
│ Desktop Client  │       │   Mobile App     │
│ (Vite / React)  │       │  (React Native)  │
└────────┬────────┘       └────────┬─────────┘
         │                         │
         ├───────────────┬─────────┘
         │ HTTP / REST   │ WebRTC (SRTP/ICE)
         ▼               ▼
┌─────────────────┐ ┌────────────────────────┐
│ FastAPI Backend │ │ LiveKit Media Server   │
│ (Control Plane) │ │ (Data/Transport Plane) │
└────────┬────────┘ └───────────┬────────────┘
         │                      │
         │ Internal RPC / Redis │ WebRTC Data/Audio Tracks
         ▼                      ▼
┌────────────────────────────────────────────┐
│          LiveKit Agent Subsystem           │
│              (Worker Plane)                │
└─────────────────────┬──────────────────────┘
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
┌───────────────────┐ ┌──────────────────────┐
│ Cloud Voice Engine│ │ Local Voice Engine   │
│ (Gemini Live API) │ │ (Ollama/Whisper/TTS) │
└───────────────────┘ └──────────────────────┘

2.2 Subsystem Responsibilities
Control Plane (Backend/app):

Issues JWTs for LiveKit room authorization.

Exposes system metrics, client configuration, and persistent database interactions.

Transport Plane (LiveKit Server + Redis):

Manages SFU (Selective Forwarding Unit) audio routing over WebRTC.

Tracks active rooms, participant state, and event dispatches via Redis.

Worker Plane (Backend/agent):

Joins target LiveKit rooms as an automated participant.

Ingests real-time PCM audio streams, handles voice activity detection (VAD), orchestrates LLM calls, and streams synthesized PCM audio back into the room.

3. Low-Level System Design (LLD)
3.1 Client Session Initialization Flow

Client                  FastAPI Server            LiveKit Server             LiveKit Agent
  │                           │                          │                         │
  │─── 1. POST /api/v1/token ─▶│                          │                         │
  │    (identity, room)       │                          │                         │
  │                           │                          │                         │
  │◀── 2. Return JWT Token ───│                          │                         │
  │                           │                          │                         │
  │─── 3. Connect (JWT) ────────────────────────────────▶│                         │
  │                                                      │─── 4. Dispatch Job ────▶│
  │                                                      │    (Room Created)       │
  │                                                      │                         │
  │                                                      │◀── 5. Join Room ────────│
  │                                                      │    (Publish Audio)      │
  │                                                                                │
  │===================== 6. Bidirectional Audio WebRTC Stream =====================│


  3.2 Agent Subsystem Class Structure (Backend/agent)

  ┌──────────────────────┐
                               │     AgentWorker      │
                               └──────────┬───────────┘
                                          │ Instantiates
                                          ▼
                               ┌──────────────────────┐
                               │     AgentSession     │
                               └──────────┬───────────┘
                                          │ Uses
                 ┌────────────────────────┴────────────────────────┐
                 ▼                                                 ▼
    ┌─────────────────────────┐                       ┌─────────────────────────┐
    │   GeminiRealtimeEngine  │                       │    LocalPipelineEngine  │
    └────────────┬────────────┘                       └────────────┬────────────┘
                 │                                                 │
                 ▼                                                 ▼
  [Google Gemini Live API]                       ┌─────────────────┼─────────────────┐
                                                 ▼                 ▼                 ▼
                                         ┌──────────────┐   ┌─────────────┐   ┌────────────┐
                                         │ Whisper (STT)│   │Ollama (LLM) │   │ Kokoro/TTS │
                                         └──────────────┘   └─────────────┘   └────────────┘



3.3 Engine Switching Strategy (State Pattern)
The Agent dynamically binds its input/output stream to an implementation conforming to the base VoiceEngine interface:

Cloud Engine (gemini_engine.py): Operates on duplex WebSockets. Audio PCM frames are forwarded directly to wss://generativelanguage.googleapis.com. Turn detection and TTS are executed server-side at Google.

Local Engine (local_engine.py): Operates on a discrete pipeline:

VAD: Silero VAD buffers incoming audio frames until speech end is detected.

STT: Speech segment sent to Whisper for local transcription.

LLM: Text prompt dispatched to local Ollama instance (llama3.2 / mistral).

TTS: Response text streamed through local TTS engine (Kokoro/Piper) to output PCM frames back to the LiveKit track.



4. Repository Directory Structure

OsmiumCore/
├── ARCHITECTURE.md                 # System Design & Architecture Specification
├── docker-compose.yml              # Infrastructure Services (LiveKit + Redis)
├── livekit.yaml                    # LiveKit SFU Configuration
│
├── scripts/                        # Environment & Service Launchers
│   ├── 1-backend.bat               # Starts FastAPI Control Server
│   ├── 2-agent.bat                 # Starts LiveKit Voice Agent
│   ├── 3-desktop.bat               # Starts Desktop Frontend
│   └── 4-mobile.bat                # Starts Mobile Frontend (Expo)
│
├── Backend/                        # Python Subsystem (Control + Worker Planes)
│   ├── .env                        # System Secrets & Keys
│   ├── requirements.txt            # Environment Dependencies
│   │
│   ├── agent/                      # LiveKit Agent Subsystem (Worker Plane)
│   │   ├── __init__.py
│   │   └── main.py                 # Worker Runner Entrypoint
│   │
│   └── app/                        # FastAPI Subsystem (Control Plane)
│       ├── __init__.py
│       ├── main.py                 # FastAPI Web Entrypoint
│       ├── api/                    # API Routing Layer
│       │   ├── __init__.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       └── token.py        # Token Minting Endpoint
│       └── core/                   # Application Configuration
│           ├── __init__.py
│           └── config.py           # Pydantic Settings
│
├── DesktopClient/                  # Web / Tauri Client Subsystem
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   └── src/
│       ├── assets/
│       ├── services/
│       │   └── api.ts              # FastAPI REST Client
│       ├── App.css
│       ├── App.tsx                 # Core UI & WebRTC Orchestrator
│       ├── index.css
│       └── main.tsx
│
└── MobileApp/                      # React Native / Expo Subsystem
    ├── .claude/
    │   └── settings.json
    ├── assets/
    ├── AGENTS.md
    ├── App.js                      # React Native Main Component
    ├── app.json
    ├── CLAUDE.md
    ├── eas.json
    ├── index.js
    └── package.json


## 5. Local Execution & Runtime Operations

### Python Virtual Environment Setup
- **Environment Manager:** Anaconda / Miniconda
- **Environment Name:** `oc` (Python 3.11)
- **Activation Command:** `conda activate oc`

### Service Matrix

| Component | Working Directory | Command | Protocol / Port |
| :--- | :--- | :--- | :--- |
| **LiveKit Server** | Root (`/`) | `docker-compose up` | WebRTC / TCP `7880` |
| **FastAPI Backend**| Root (`/`) | `python -m uvicorn Backend.app.main:app --reload --host 0.0.0.0 --port 8000` | REST / HTTP `8000` |
| **LiveKit Agent**  | `Backend/` | `python -m agent.main dev` | Internal RPC / WS |
| **Desktop Client** | `DesktopClient/` | `npm run dev` | HTTP `5173` |
| **Mobile App**      | `MobileApp/` | `npx expo start` | Metro / Expo `8081` |


6. Failure Modes & Operational Recovery
WebSocket Network Severance (WinError 64 / 1006):

Root Cause: Sudden network interface state change or host TCP socket reset during active Cloud S2S streaming.

Mitigation: The agent catches non-recoverable WebSocket connection errors, cleans up the active session state, and terminates cleanly. Use scripts/2-agent.bat to re-instantiate the worker process.

Missing Import Context:

Root Cause: Running agent execution files directly without module path context (python Backend/agent/main.py).

Mitigation: Always execute the agent as a module from within the Backend/ directory (python -m agent.main dev).