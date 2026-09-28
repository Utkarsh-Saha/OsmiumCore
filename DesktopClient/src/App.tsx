import { useState, useEffect } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  VoiceAssistantControlBar,
  BarVisualizer,
  useVoiceAssistant,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { fetchLiveKitToken } from "./services/api";
import type { TokenResponse } from "./services/api";
import { TextChat } from "./components/TextChat";

function VoiceAgentUI() {
  const { state, audioTrack } = useVoiceAssistant();

  return (
    <div className="voice-card">
      <div className="voice-header">
        <h2 className="section-title">Live Voice Agent</h2>
        <p className="status">
          Status: <span className="status-value">{state}</span>
        </p>
      </div>

      <div className="visualizer-card">
        <BarVisualizer state={state} barCount={7} trackRef={audioTrack} style={{ height: "60px", width: "100%" }} />
      </div>

      <VoiceAssistantControlBar controls={{ leave: false }} />
    </div>
  );
}

export default function App() {
  const [connectionInfo, setConnectionInfo] = useState<TokenResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState<string>("user-desktop-1");

  useEffect(() => {
    const stored = localStorage.getItem("osmium_user_id");
    if (stored) {
      setUserId(stored);
    } else {
      const generated = "user-" + Math.floor(1000 + Math.random() * 9000);
      localStorage.setItem("osmium_user_id", generated);
      setUserId(generated);
    }
  }, []);

  const startSession = async () => {
    setLoading(true);
    try {
      const data = await fetchLiveKitToken("osmiumcore-default", userId);
      setConnectionInfo(data);
    } catch (err) {
      console.error("Failed to connect to LiveKit:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="main-layout">
      <header className="app-header">
        <div className="logo-badge">
          <span className="logo-icon">⚡</span>
          <h1 className="title">OSMIUMCORE</h1>
        </div>
        <div className="header-meta">
          <span className="user-indicator">Identity: <strong>{userId}</strong></span>
        </div>
      </header>

      <div className="workspace-grid">
        {/* Voice Channel Section */}
        <section className="panel voice-panel">
          {!connectionInfo ? (
            <div className="voice-connect-box">
              <h3>Real-Time Voice Channel</h3>
              <p className="panel-desc">Connect directly to the LiveKit voice assistant for conversational speech.</p>
              <button onClick={startSession} disabled={loading} className="btn-primary">
                {loading ? "Connecting..." : "Connect Voice Assistant"}
              </button>
            </div>
          ) : (
            <LiveKitRoom
              serverUrl={connectionInfo.server_url}
              token={connectionInfo.token}
              connect={true}
              audio={true}
              video={false}
              onDisconnected={() => setConnectionInfo(null)}
            >
              <VoiceAgentUI />
              <RoomAudioRenderer />
            </LiveKitRoom>
          )}
        </section>

        {/* Text & Whisper Transcription Section */}
        <section className="panel chat-panel">
          <TextChat userId={userId} sessionId={`session-${userId}`} />
        </section>
      </div>
    </div>
  );
}