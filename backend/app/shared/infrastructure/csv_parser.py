import csv
import io


def parse_csv(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Generic CSV parsing utility shared by every data_import/ importer.
    Decodes as utf-8-sig so a BOM from an Excel-exported CSV doesn't end up
    prefixed onto the first header name.
    """
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = [dict(row) for row in reader]
    return list(headers), rows
