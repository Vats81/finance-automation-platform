import pytest

from app.shared.domain.exceptions import ValidationException
from app.shared.infrastructure.csv_parser import MAX_ROWS, MAX_UPLOAD_BYTES, parse_csv


def test_parses_a_plain_csv() -> None:
    headers, rows = parse_csv(b"name,city\nAcme,Austin\n")

    assert headers == ["name", "city"]
    assert rows == [{"name": "Acme", "city": "Austin"}]


def test_strips_a_utf8_bom() -> None:
    headers, _ = parse_csv(b"\xef\xbb\xbfname,city\nAcme,Austin\n")

    assert headers == ["name", "city"]


def test_falls_back_to_windows_1252_for_excel_csvs() -> None:
    _, rows = parse_csv("name\nCafé Müller\n".encode("cp1252"))

    assert rows == [{"name": "Café Müller"}]


@pytest.mark.parametrize(
    "content",
    [
        b"PK\x03\x04\x00\x00\x00\x00 an xlsx is a zip",
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
        b"%PDF-1.7\n\x00\x01\x02",
        bytes(range(256)),
    ],
)
def test_rejects_binary_files_with_a_validation_error(content: bytes) -> None:
    with pytest.raises(ValidationException):
        parse_csv(content)


@pytest.mark.parametrize("delimiter", [";", "\t", "|"])
def test_detects_other_delimiters(delimiter: str) -> None:
    headers, rows = parse_csv(f"name{delimiter}city\nAcme{delimiter}Austin\n".encode())

    assert headers == ["name", "city"]
    assert rows == [{"name": "Acme", "city": "Austin"}]


def test_commas_inside_quotes_are_not_delimiters() -> None:
    _, rows = parse_csv(b'name,city\n"Acme, Inc",Austin\n')

    assert rows[0]["name"] == "Acme, Inc"


def test_empty_file_yields_no_headers_or_rows() -> None:
    assert parse_csv(b"") == ([], [])


def test_rejects_files_over_the_size_limit() -> None:
    with pytest.raises(ValidationException, match="too large"):
        parse_csv(b"a" * (MAX_UPLOAD_BYTES + 1))


def test_rejects_files_with_too_many_rows() -> None:
    content = b"name\n" + b"x\n" * (MAX_ROWS + 1)

    with pytest.raises(ValidationException, match="rows"):
        parse_csv(content)
