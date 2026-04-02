import re

MAX_CLAIM_LENGTH = 750
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
    claim = re.sub(r'</?\s*\w[\w\s]*>', '', claim)
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


def validate_document_paths(document_paths, participant_id: str) -> list[str]:
    if document_paths is None:
        return []
    if not isinstance(document_paths, list):
        raise ValueError("Invalid document paths")

    prefix = f"users/{participant_id}/documents/"
    valid_paths = []
    for path in document_paths:
        if not isinstance(path, str):
            raise ValueError("Invalid document path")
        if not path.startswith(prefix):
            raise ValueError("Invalid uploaded document reference")
        if ".." in path or "\\" in path or path.endswith("/"):
            raise ValueError("Invalid uploaded document reference")
        filename = path[len(prefix):]
        if not filename or "/" in filename:
            raise ValueError("Invalid uploaded document reference")
        valid_paths.append(path)

    return valid_paths
