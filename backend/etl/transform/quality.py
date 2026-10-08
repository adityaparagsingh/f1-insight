"""Data-quality checks and run statistics for the ETL."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Hashable, Iterable, Iterator, Optional


@dataclass
class EtlStats:
    """Mutable counters for one pipeline run."""

    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    duplicates_removed: int = 0
    missing_values_fixed: int = 0
    invalid_values_fixed: int = 0
    errors: int = 0
    issues: list[str] = field(default_factory=list)
    _max_issues: int = 50

    def issue(self, message: str) -> None:
        self.errors += 1
        if len(self.issues) < self._max_issues:
            self.issues.append(message)

    def note(self, message: str) -> None:
        """Non-error anomaly note (capped list)."""
        if len(self.issues) < self._max_issues:
            self.issues.append(f"note: {message}")

    @property
    def quality_summary(self) -> str:
        return (
            f"extracted={self.records_extracted} transformed={self.records_transformed} "
            f"loaded={self.records_loaded} duplicates_removed={self.duplicates_removed} "
            f"missing_fixed={self.missing_values_fixed} invalid_fixed={self.invalid_values_fixed} "
            f"errors={self.errors}"
        )

    def as_dict(self) -> dict:
        return {
            "records_extracted": self.records_extracted,
            "records_transformed": self.records_transformed,
            "records_loaded": self.records_loaded,
            "duplicates_removed": self.duplicates_removed,
            "missing_values_fixed": self.missing_values_fixed,
            "invalid_values_fixed": self.invalid_values_fixed,
            "errors": self.errors,
            "issues": list(self.issues),
        }


def dedupe(
    rows: Iterable[dict],
    key_fn: Callable[[dict], Hashable],
    stats: EtlStats,
) -> Iterator[dict]:
    """Drop duplicate rows by natural key, counting removals in ``stats``."""
    seen: set[Hashable] = set()
    for row in rows:
        key = key_fn(row)
        if key in seen:
            stats.duplicates_removed += 1
            continue
        seen.add(key)
        yield row


def clamp_position(value: Optional[int], stats: EtlStats, field_name: str = "position") -> Optional[int]:
    """Positions must be positive integers or None. Invalid -> None."""
    if value is None:
        return None
    if value < 0 or value > 60:
        stats.invalid_values_fixed += 1
        stats.note(f"invalid {field_name}={value} normalised to NULL")
        return None
    return value


def require_reference(
    stats: EtlStats,
    kind: str,
    key: Optional[str],
    context: str,
) -> bool:
    """Check that a driver/constructor/circuit/race reference exists."""
    if key:
        return True
    stats.issue(f"missing {kind} reference in {context}")
    return False
