from decimal import Decimal


def _group_indian(whole: str) -> str:
    """12345678 -> 1,23,45,678 (the last three digits, then pairs)."""
    if len(whole) <= 3:
        return whole
    head, tail = whole[:-3], whole[-3:]
    pairs: list[str] = []
    while len(head) > 2:
        pairs.insert(0, head[-2:])
        head = head[:-2]
    return ",".join([head, *pairs, tail] if head else [*pairs, tail])


def format_money(amount: Decimal, currency: str = "USD", *, plain: bool = False) -> str:
    """-$5.00, not $-5.00, for a loss. Rupees are grouped the Indian way (1,23,456.00) and use the
    rupee sign, or "Rs." with plain=True for places whose font has no rupee sign (the PDF report).
    """
    sign = "-" if amount < 0 else ""
    if currency == "INR":
        whole, _, cents = f"{abs(amount):.2f}".partition(".")
        symbol = "Rs. " if plain else "₹"
        return f"{sign}{symbol}{_group_indian(whole)}.{cents}"
    return f"{sign}${abs(amount):,.2f}"
