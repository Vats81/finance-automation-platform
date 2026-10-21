import pytest

from app.data_import.api.routes import _parse_column_mapping
from app.shared.domain.exceptions import ValidationException


def test_accepts_an_object_of_text_headers_and_drops_blank_ones() -> None:
    mapping = _parse_column_mapping('{"name": "Customer", "phone": null, "email": ""}')

    assert mapping == {"name": "Customer"}


@pytest.mark.parametrize("raw", ["not json", "[1, 2]", '"a string"', "42", "null", '{"name": 5}'])
def test_rejects_anything_that_is_not_a_field_to_header_object(raw: str) -> None:
    # These all used to escape as a 500 (JSON error, or AttributeError on .get()).
    with pytest.raises(ValidationException):
        _parse_column_mapping(raw)
