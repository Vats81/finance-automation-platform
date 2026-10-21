import csv
import io

from app.shared.domain.exceptions import ValidationException

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_ROWS = 3000

_DELIMITERS = ",;\t|"


def _decode(content: bytes) -> str:
    # NUL bytes never appear in a text CSV: this is an .xlsx/.zip/image/PDF
    # (or random bytes) renamed or exported by mistake. Decoding those used to
    # raise UnicodeDecodeError -> 500.
    if b"\x00" in content[:8192]:
        raise ValidationException(
            "This doesn't look like a CSV file. If it's an Excel file, use Save As > CSV first."
        )
    try:
        # utf-8-sig so a BOM from an Excel-exported CSV doesn't end up
        # prefixed onto the first header name.
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Excel on Windows saves "CSV" as Windows-1252, so accented names
        # (e.g. "Café", "Müller") aren't valid UTF-8.
        return content.decode("cp1252", errors="replace")


def _sniff_delimiter(text: str) -> str:
    header = text.lstrip("\r\n").split("\n", 1)[0]
    counts = {d: header.count(d) for d in _DELIMITERS}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] > 0 else ","


def parse_csv(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Generic CSV parsing utility shared by every data_import/ importer.

    Tolerates the usual spreadsheet exports (BOM, Windows-1252, semicolon- or
    tab-separated) and rejects what can't be an import file with a
    ValidationException (422) rather than letting it surface as a 500.
    """
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationException(
            f"This file is too large ({len(content) // (1024 * 1024)} MB). "
            f"The limit is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB; split it into smaller files."
        )
    text = _decode(content)
    reader = csv.DictReader(io.StringIO(text), delimiter=_sniff_delimiter(text))
    try:
        headers = reader.fieldnames or []
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({k: v for k, v in row.items() if k is not None})
            if len(rows) > MAX_ROWS:
                raise ValidationException(
                    f"This file has more than {MAX_ROWS:,} rows. "
                    "Split it into smaller files and import them one at a time."
                )
    except csv.Error as exc:
        raise ValidationException(f"Could not read this CSV: {exc}") from exc
    return list(headers), rows
