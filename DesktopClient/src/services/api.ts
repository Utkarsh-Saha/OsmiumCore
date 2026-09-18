export interface TokenResponse {
  token: string;
  server_url: string;
}

export async function fetchLiveKitToken(
  roomName: string = "osmiumcore-default",
  identity: string = "user-" + Math.floor(Math.random() * 10000)
): Promise<TokenResponse> {
  const response = await fetch("http://localhost:8000/api/v1/token", {
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