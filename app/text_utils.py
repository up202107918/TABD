"""
Repair Portuguese text corrupted by UTF-8 bytes mis-decoded as Windows-1250 (common on PL Windows).
"""


def repair_utf8_cp1250_mojibake(text: str | None) -> str | None:
    """
    Reverse: good_utf8.decode('cp1250') -> broken_unicode stored in DB.
    Rebuild original UTF-8 bytes and decode as UTF-8.
    """
    if not text:
        return text

    raw = bytearray()
    for char in text:
        try:
            raw.extend(char.encode('cp1250'))
        except UnicodeEncodeError:
            code = ord(char)
            if code < 256:
                raw.append(code)

    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return text
