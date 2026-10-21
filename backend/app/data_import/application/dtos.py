from collections.abc import Callable
from dataclasses import dataclass, field

# (rows processed so far, total rows)
ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class ImportRowError:
    row_number: int
    message: str


@dataclass(frozen=True)
class ImportSummary:
    total_rows: int
    created: int
    skipped_duplicates: int
    errors: list[ImportRowError] = field(default_factory=list)
