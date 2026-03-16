import time
from collections import defaultdict
import asyncio

class RateLimiter:
    def __init__(self):
        # { sid: [timestamp, ...] }
        self._session_starts = defaultdict(list)
        self._audio_chunks = defaultdict(list)
        self._connections = defaultdict(list)  # { ip: [timestamp, ...] }
        self._extract_claims = defaultdict(list)  # { uid: [timestamp, ...] }

    def _clean_window(self, timestamps: list, window_seconds: int) -> list:
        cutoff = time.time() - window_seconds
        return [t for t in timestamps if t > cutoff]

    def check_connection(self, ip: str) -> bool:
        """Max 10 connections per IP per minute"""
        self._connections[ip] = self._clean_window(self._connections[ip], 60)
        if len(self._connections[ip]) >= 10:
            return False
        self._connections[ip].append(time.time())
        return True

    def check_session_start(self, sid: str) -> bool:
        """Max 5 session starts per socket per 10 minutes"""
        self._session_starts[sid] = self._clean_window(self._session_starts[sid], 600)
        if len(self._session_starts[sid]) >= 5:
            return False
        self._session_starts[sid].append(time.time())
        return True

    def check_audio_chunk(self, sid: str) -> bool:
        """Max 200 audio chunks per second per session (worklet sends ~50/s normally)"""
        self._audio_chunks[sid] = self._clean_window(self._audio_chunks[sid], 1)
        if len(self._audio_chunks[sid]) >= 200:
            return False
        self._audio_chunks[sid].append(time.time())
        return True

    def check_extract_claim(self, uid: str) -> bool:
        """Max 3 claim extractions per user per 10 minutes."""
        self._extract_claims[uid] = self._clean_window(self._extract_claims[uid], 600)
        if len(self._extract_claims[uid]) >= 3:
            return False
        self._extract_claims[uid].append(time.time())
        return True

    def clear_sid(self, sid: str):
        self._session_starts.pop(sid, None)
        self._audio_chunks.pop(sid, None)

limiter = RateLimiter()