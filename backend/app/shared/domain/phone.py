def whatsapp_number(raw: str | None, currency: str = "USD") -> str | None:
    """A phone number in the +country-code form WhatsApp sending needs, or None if it does not look like one.
    A number with no country code is taken as Indian (+91) for a rupee business, and is refused otherwise
    because the country cannot be guessed.
    """
    if not raw:
        return None
    text = raw.strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if text.startswith("+"):
        return f"+{digits}" if 8 <= len(digits) <= 15 else None
    digits = digits.lstrip("0")
    if currency == "INR":
        if len(digits) == 10:
            return f"+91{digits}"
        if len(digits) == 12 and digits.startswith("91"):
            return f"+{digits}"
    return None
