from nanoid import generate

def generate_short_id(size: int = 8) -> str:
    """
    Generates a secure, URL-safe random string using NanoID.
    Default alphabet: A-Za-z0-9_-
    """
    return generate(size=size)
