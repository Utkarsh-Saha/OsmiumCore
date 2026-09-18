# OsmiumCore

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-brightgreen.svg)](https://www.python.org/)
[![LiveKit](https://img.shields.io/badge/LiveKit-WebRTC-orange.svg)](https://livekit.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%20%7C%20Expo-61DAFB.svg)](https://react.dev/)

An open-source, production-grade, voice-first AI assistant ecosystem designed with clean architecture for sub-second (<800ms) real-time speech-to-speech interaction across Desktop and Mobile devices.

---

## 🏗️ Architecture Overview

OsmiumCore decouples voice transport from business control logic:

- **Transport Plane (LiveKit SFU + Redis):** Real-time WebRTC audio streaming, track subscriptions, and audio frame forwarding.
- **Control Plane (FastAPI):** Zero-trust LiveKit JWT minting, authentication, session tokens, and system health endpoints.
- **Worker Plane (LiveKit Agents):** Automated room agent orchestrating real-time audio sessions with Google Gemini Live API (`gemini-2.5-flash-native-audio`) and local engine pipelines.
- **Clients:**
  - **Desktop Client:** React + Vite + TypeScript interface with LiveKit audio renderer and real-time audio visualizers.
  - **Mobile App:** React Native + Expo audio session client.

For deep technical details, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 📁 Repository Structure

```
OsmiumCore/
├── ARCHITECTURE.md                 # System Architecture & Technical Specification
├── docker-compose.yml              # Infrastructure Services (LiveKit SFU + Redis)
├── livekit.yaml                    # LiveKit SFU Configuration
├── scripts/                        # Service Launchers (.bat for Windows)
│   ├── 1-backend.bat               # Starts FastAPI Control Server
│   ├── 2-agent.bat                 # Starts LiveKit Voice Agent
│   ├── 3-desktop.bat               # Starts Desktop Frontend
│   └── 4-mobile.bat                # Starts Mobile Frontend (Expo)
│
├── Backend/                        # Control Plane & Worker Plane (Python)
│   ├── .env.example                # Environment variables template
│   ├── requirements.txt            # Python dependencies
│   ├── app/                        # FastAPI Control Plane
│   └── agent/                      # LiveKit Agent Worker Subsystem
│
├── DesktopClient/                  # Desktop Frontend (React + Vite + TypeScript)
│   ├── src/
│   └── package.json
│
└── MobileApp/                      # Mobile Frontend (React Native + Expo)
    ├── App.js
    └── package.json
```

---

## 🚀 Quick Start

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for LiveKit SFU + Redis)
- [Conda](https://docs.conda.io/en/latest/) with Python 3.11 (`conda create -n oc python=3.11`)
- [Node.js](https://nodejs.org/) (v18+ or v20+)

### 2. Environment Configuration
Copy the sample environment file in `Backend/` and configure your API keys:
```bash
cp Backend/.env.example Backend/.env
```
Update `Backend/.env` with your `GOOGLE_API_KEY` and any local LLM settings.

### 3. Install Dependencies
```bash
# Python Backend & Agent
conda activate oc
pip install -r Backend/requirements.txt

# Desktop Frontend
cd DesktopClient
npm install
cd ..

# Mobile Frontend
cd MobileApp
npm install
cd ..
```

### 4. Running the Services

#### Option A: Quick Launch Scripts (Windows)
Run the numbered scripts inside the `scripts/` directory in sequence:
1. `docker compose up -d` (start LiveKit & Redis)
2. `scripts\1-backend.bat`
3. `scripts\2-agent.bat`
4. `scripts\3-desktop.bat`
5. `scripts\4-mobile.bat`

#### Option B: Manual Terminal Launch
| Service | Working Directory | Command | Port |
| :--- | :--- | :--- | :--- |
| **LiveKit Server** | Root (`/`) | `docker compose up -d` | `7880` |
| **FastAPI Backend** | Root (`/`) | `python -m uvicorn Backend.app.main:app --reload --host 0.0.0.0 --port 8000` | `8000` |
| **LiveKit Agent** | `Backend/` | `python -m agent.main dev` | Internal RPC |
| **Desktop Client** | `DesktopClient/` | `npm run dev` | `5173` |
| **Mobile App** | `MobileApp/` | `npx expo start` | `8081` |

---

## 📄 License
This project is licensed under the MIT License.
