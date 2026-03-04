import re

MAX_CLAIM_LENGTH = 500
MAX_AUDIO_CHUNK_BYTES = 32768  # 32KB max per chunk

def sanitize_claim(claim: str) -> str:
    if not isinstance(claim, str):
        raise ValueError("Claim must be a string")
    
    claim = claim.strip()
    
    if not claim:
        raise ValueError("Claim cannot be empty")
    
    if len(claim) > MAX_CLAIM_LENGTH:
        raise ValueError(f"Claim exceeds {MAX_CLAIM_LENGTH} character limit")
    
    # Strip any injection attempts — remove control characters
    claim = re.sub(r'[\x00-\x1f\x7f]', '', claim)
    
    # Collapse excessive whitespace
    claim = re.sub(r'\s+', ' ', claim)
    
    return claim

def validate_audio_chunk(data) -> bytes:
    if data is None:
        raise ValueError("No audio data")
    
    raw = bytes(data)
    
    if len(raw) == 0:
        raise ValueError("Empty audio chunk")
    
    if len(raw) > MAX_AUDIO_CHUNK_BYTES:
        raise ValueError(f"Audio chunk too large: {len(raw)} bytes")
    
    return raw

def validate_participant_id(pid: str) -> str:
    if not isinstance(pid, str):
        raise ValueError("Invalid participant ID")
    # Only allow alphanumeric, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9_\-]{1,64}$', pid):
        raise ValueError("Invalid participant ID format")
    return pid