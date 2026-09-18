import asyncio
import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli
from livekit.plugins import google

load_dotenv()

# Pre-flight environment check
if not os.getenv("GOOGLE_API_KEY"):
    print("WARNING: GOOGLE_API_KEY is not set in backend environment variables.")

class OsmiumAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are OsmiumCore, a composed, intelligent, voice-first desktop AI assistant. "
                "Keep responses concise, clear, and natural for speech output."
            )
        )

server = AgentServer()

@server.rtc_session
async def entrypoint(ctx: JobContext):
    # 1. Join the LiveKit RTC room first
    await ctx.connect()

    # 2. Initialize Gemini Live API realtime model session
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Puck",
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    )

    # 3. Start the session in the room
    await session.start(
        agent=OsmiumAssistant(),
        room=ctx.room,
    )

    # 4. Initial voice greeting when client connects
    await session.generate_reply(
        instructions="Greet the user warmly as OsmiumCore and ask how you can assist."
    )

if __name__ == "__main__":
    cli.run_app(server)