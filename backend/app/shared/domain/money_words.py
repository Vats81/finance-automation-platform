"""An amount in words the Indian way, for the line at the foot of an invoice:
"Rupees One Lakh Twenty Three Thousand Four Hundred Fifty Six and Fifty Paise Only".
"""

from decimal import ROUND_HALF_UP, Decimal

_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
    "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen",
]  # fmt: skip
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _below_hundred(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return _TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")


def _below_thousand(n: int) -> str:
    words = []
    if n >= 100:
        words.append(_ONES[n // 100] + " Hundred")
        n %= 100
    if n:
        words.append(_below_hundred(n))
    return " ".join(words)


def number_to_words_indian(n: int) -> str:
    """Whole numbers in crores, lakhs, thousands and hundreds. 0 is "Zero"."""
    if n == 0:
        return "Zero"
    parts = []
    if n >= 10_000_000:  # crores can themselves run to hundreds of crores
        parts.append(number_to_words_indian(n // 10_000_000) + " Crore")
        n %= 10_000_000
    for size, name in ((100_000, "Lakh"), (1000, "Thousand")):
        if n >= size:
            parts.append(_below_hundred(n // size) + " " + name)
            n %= size
    if n:
        parts.append(_below_thousand(n))
    return " ".join(parts)


def rupees_in_words(amount: Decimal) -> str:
    """ "Rupees ... and ... Paise Only". Negative amounts are written without the sign."""
    value = abs(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rupees = int(value)
    paise = int((value - rupees) * 100)
    words = f"Rupees {number_to_words_indian(rupees)}"
    if paise:
        words += f" and {number_to_words_indian(paise)} Paise"
    return words + " Only"
