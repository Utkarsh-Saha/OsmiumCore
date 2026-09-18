import { useState } from "react";
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

function VoiceAgentUI() {
  const { state, audioTrack } = useVoiceAssistant();

  return (
    <div className="app-container">
      <div>
        <h1 className="title">OSMIUMCORE</h1>
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

  const startSession = async () => {
    setLoading(true);
    try {
      const data = await fetchLiveKitToken();
      setConnectionInfo(data);
    } catch (err) {
      console.error("Failed to connect to LiveKit:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!connectionInfo) {
    return (
      <div className="app-container">
        <h1 className="title">OSMIUMCORE</h1>
        <button onClick={startSession} disabled={loading} className="btn-primary">
          {loading ? "Initializing..." : "Connect Voice Assistant"}
        </button>
      </div>
    );
  }

  return (
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
  );
}