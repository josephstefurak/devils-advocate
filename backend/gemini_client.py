import asyncio
import base64
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-native-audio-latest"

class GeminiLiveClient:
    def __init__(self, system_prompt: str, on_text: callable, on_audio: callable, on_user_text: callable = None, on_reasoning: callable = None):
        self.system_prompt = system_prompt
        self.on_text = on_text
        self.on_audio = on_audio
        self.on_user_text = on_user_text
        self.on_reasoning = on_reasoning
        self.session = None
        self.running = False
        self._task = None

    async def connect(self):
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=self.system_prompt,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            
        )
        self._context = client.aio.live.connect(model=MODEL, config=config)
        self.session = await self._context.__aenter__()
        self.running = True
        self._task = asyncio.create_task(self._listen())

    async def send_audio(self, audio_bytes: bytes):
        if not self.session or not self.running:
            return
        try:
            await self.session.send_realtime_input(
                audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
            )
        except Exception:
            self.running = False

    async def _listen(self):
        agent_transcript_buffer = ""
        user_transcript_buffer = ""
        try:
            while self.running:
                async for msg in self.session.receive():
                    if not self.running:
                        return
                    sc = msg.server_content
                    if not sc:
                        continue
                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if part.text and self.on_reasoning:
                                await self.on_reasoning(part.text.strip())
                            if part.inline_data and "audio" in part.inline_data.mime_type:
                                # Flush user transcript when agent starts responding
                                if user_transcript_buffer.strip() and self.on_user_text:
                                    await self.on_user_text(user_transcript_buffer.strip())
                                    user_transcript_buffer = ""
                                audio_b64 = base64.b64encode(part.inline_data.data).decode()
                                await self.on_audio(audio_b64)
                    if sc.input_transcription:
                        user_transcript_buffer += sc.input_transcription.text or ""
                    if sc.output_transcription:
                        agent_transcript_buffer += sc.output_transcription.text or ""
                    if sc.turn_complete:
                        if agent_transcript_buffer.strip():
                            await self.on_text(agent_transcript_buffer.strip())
                            agent_transcript_buffer = ""
                        if user_transcript_buffer.strip() and self.on_user_text:
                            await self.on_user_text(user_transcript_buffer.strip())
                            user_transcript_buffer = ""
        except Exception as e:
            print(f"Listen error: {e}")
            self.running = False
            
    async def close(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        try:
            if self._context:
                await self._context.__aexit__(None, None, None)
        except Exception:
            pass