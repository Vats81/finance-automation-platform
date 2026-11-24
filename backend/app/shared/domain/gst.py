"""India GST identifiers an invoice needs: the GSTIN, the state code, a PIN code and a UPI ID.

Each cleaner returns the tidied value or raises ValidationException with a message a shop owner
can act on. A GSTIN is checked for shape, for a real state code and for its check character, so
a mistyped digit is caught when it is entered, not when a customer's accountant spots it.
"""

import re
from decimal import ROUND_HALF_UP, Decimal

from app.shared.domain.exceptions import ValidationException

# GST state and union territory codes (the first two digits of a GSTIN).
GST_STATES: dict[str, str] = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",
    "99": "Centre Jurisdiction",
}

_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_PINCODE_RE = re.compile(r"^[1-9][0-9]{5}$")
_UPI_RE = re.compile(r"^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z0-9]{2,64}$")


def gstin_check_character(first_fourteen: str) -> str:
    """The 15th character of a GSTIN, calculated from the first 14 (base-36 weighted checksum)."""
    total = 0
    for index, char in enumerate(first_fourteen):
        product = _CHARS.index(char) * (1 if index % 2 == 0 else 2)
        total += product // 36 + product % 36
    return _CHARS[(36 - total % 36) % 36]


def clean_gstin(value: str) -> str:
    gstin = value.strip().upper()
    if not _GSTIN_RE.match(gstin):
        raise ValidationException("A GSTIN has 15 characters, for example 27AAPFU0939F1ZV.")
    if gstin[:2] not in GST_STATES:
        raise ValidationException("The first two digits of this GSTIN are not a valid state code.")
    if gstin_check_character(gstin[:14]) != gstin[14]:
        raise ValidationException("This GSTIN's last character does not match the others. Please check it.")
    return gstin


def clean_state_code(value: str) -> str:
    code = value.strip()
    if code not in GST_STATES:
        raise ValidationException("That is not a valid GST state code.")
    return code


def clean_pincode(value: str) -> str:
    pincode = value.strip()
    if not _PINCODE_RE.match(pincode):
        raise ValidationException("A PIN code has 6 digits.")
    return pincode


def clean_upi_id(value: str) -> str:
    upi = value.strip()
    if not _UPI_RE.match(upi):
        raise ValidationException("A UPI ID looks like name@bank.")
    return upi


# The GST rates in use on goods and services, in percent.
GST_RATES: tuple[Decimal, ...] = tuple(Decimal(r) for r in ("0", "0.25", "3", "5", "12", "18", "28"))
_HSN_RE = re.compile(r"^[0-9]{4,8}$")
_CENT = Decimal("0.01")


def clean_gst_rate(value: Decimal) -> Decimal:
    if value not in GST_RATES:
        raise ValidationException("GST rate must be one of 0, 0.25, 3, 5, 12, 18 or 28 percent.")
    return value


def clean_hsn(value: str) -> str:
    hsn = value.strip()
    if not _HSN_RE.match(hsn):
        raise ValidationException("An HSN or SAC code has 4 to 8 digits.")
    return hsn


def split_tax(tax: Decimal, *, inter_state: bool) -> tuple[Decimal, Decimal, Decimal]:
    """(CGST, SGST, IGST) for one tax amount. Within a state the tax is split in two equal halves (the
    odd paisa goes to SGST); between states it is all IGST.
    """
    if inter_state:
        return Decimal("0.00"), Decimal("0.00"), tax
    cgst = (tax / 2).quantize(_CENT, rounding=ROUND_HALF_UP)
    if cgst * 2 > tax:
        cgst -= _CENT
    return cgst, tax - cgst, Decimal("0.00")
