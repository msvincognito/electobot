import uuid

def gen_token() -> str:
    """Returns a random token."""
    return str(uuid.uuid4())
