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
    def __init__(self, system_prompt: str, on_text: callable, on_audio: callable, on_user_text: callable = None, on_reasoning: callable = None, on_grounding: callable = None, on_interrupted: callable = None, on_error: callable = None, voice_name="Charon"):
        self.system_prompt = system_prompt
        self.on_text = on_text
        self.on_audio = on_audio
        self.on_user_text = on_user_text
        self.on_reasoning = on_reasoning
        self.session = None
        self.running = False
        self._task = None
        self.on_grounding = on_grounding
        self.on_interrupted = on_interrupted
        self.on_error = on_error
        self.voice_name = voice_name
        self._user_transcript_buffer = ""
        self._agent_transcript_buffer = ""

    async def connect(self):
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=self.system_prompt,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice_name)
                )
            ),
            tools=[
                types.Tool(google_search=types.GoogleSearch())
            ],
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
        except Exception as e:
            print(f"Audio send error: {e}")
            self.running = False
            if self.on_error:
                await self.on_error("Connection to debate engine lost. Please end and start a new session.")

    async def _listen(self):
        
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
                                if self._user_transcript_buffer.strip() and self.on_user_text:
                                    await self.on_user_text(self._user_transcript_buffer.strip(), partial=False)
                                    self._user_transcript_buffer = ""
                                audio_b64 = base64.b64encode(part.inline_data.data).decode()
                                await self.on_audio(audio_b64)
                    if sc.input_transcription:
                        chunk = sc.input_transcription.text or ""
                        if chunk:
                            self._user_transcript_buffer += chunk
                            if self.on_user_text:
                                await self.on_user_text(chunk, partial=True)
                    if sc.output_transcription:
                        chunk = sc.output_transcription.text or ""
                        if chunk:
                            self._agent_transcript_buffer += chunk
                            await self.on_text(chunk, partial=True)
                    if sc.turn_complete:
                        if self._agent_transcript_buffer.strip():
                            await self.on_text(self._agent_transcript_buffer.strip(), partial=False)
                            self._agent_transcript_buffer = ""
                        else: 
                            print(f"turn_complete with empty transcript buffer — audio-only turn")
                        if self._user_transcript_buffer.strip() and self.on_user_text:
                            await self.on_user_text(self._user_transcript_buffer.strip(), partial=False)
                            self._user_transcript_buffer = ""
                    if sc.grounding_metadata and self.on_grounding:
                        await self.on_grounding(sc.grounding_metadata)
                    if sc.interrupted:
                        if self._agent_transcript_buffer.strip():
                            await self.on_text(self._agent_transcript_buffer.strip(), partial=False)
                        self._agent_transcript_buffer = ""
                        self._user_transcript_buffer = ""
                        if self.on_interrupted:
                            await self.on_interrupted()

        except Exception as e:
            print(f"Listen error: {e}")
            self.running = False

    async def send_context(self, context_text: str):
        if not self.session or not self.running or not context_text.strip():
            return
        try:
            await self.session.send_client_content(
                turns=[{"role": "user", "parts": [{"text": context_text}]}],
                turn_complete=False
            )
        except Exception as e:
            print(f"Context injection error: {e}")

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