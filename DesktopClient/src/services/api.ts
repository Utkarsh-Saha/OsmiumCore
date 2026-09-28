export interface TokenResponse {
  token: string;
  server_url: string;
}

export interface MessageResponse {
  status: string;
  user_id: string;
  session_id: string;
  user_message: string;
  reply: string;
}

export interface TranscribeResponse {
  text: string;
  user_id: string;
  session_id: string;
}

const API_BASE_URL = "http://localhost:8000/api/v1";

export async function fetchLiveKitToken(
  roomName: string = "osmiumcore-default",
  identity: string = "user-" + Math.floor(Math.random() * 10000)
): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      room_name: roomName,
      participant_identity: identity,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch token: ${response.statusText}`);
  }

  return response.json();
}

export async function sendTextMessage(
  userId: string,
  content: string,
  sessionId?: string
): Promise<MessageResponse> {
  const response = await fetch(`${API_BASE_URL}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      content: content,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => null);
    throw new Error(errData?.detail || `Failed to send message (${response.status})`);
  }

  return response.json();
}

export async function transcribeAudioFile(
  userId: string,
  audioBlob: Blob | File,
  sessionId?: string
): Promise<TranscribeResponse> {
  const formData = new FormData();
  formData.append("user_id", userId);
  if (sessionId) {
    formData.append("session_id", sessionId);
  }
  formData.append("audio", audioBlob, "recording.wav");

  const response = await fetch(`${API_BASE_URL}/transcribe`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => null);
    throw new Error(errData?.detail || `Failed to transcribe audio (${response.status})`);
  }

  return response.json();
}