"""The DuckDB warehouse: schema, connection, and the queries that produce
conversion paths for the attribution layer.

Local-first by design: the entire product demos offline against one file.
The BigQuery-sandbox and Databricks-Free-Edition adapters implement the same
tiny interface (`paths()`, `spend()`) against remote warehouses; DuckDB is the
reference implementation and the offline mirror that makes the remote tiers
reproducible after their quotas and expiries bite.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import duckdb

from .attribution import ConversionPath, Touchpoint

SCHEMA = """
CREATE TABLE IF NOT EXISTS spend (
    channel VARCHAR NOT NULL,
    day     DATE    NOT NULL,
    amount  DOUBLE  NOT NULL,
    PRIMARY KEY (channel, day)
);
CREATE TABLE IF NOT EXISTS conversions (
    conversion_id VARCHAR PRIMARY KEY,
    user_id       VARCHAR NOT NULL,
    revenue       DOUBLE  NOT NULL,
    converted_at  TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS touchpoints (
    conversion_id VARCHAR NOT NULL REFERENCES conversions(conversion_id),
    channel       VARCHAR NOT NULL,
    ts            TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS touchpoints_conversion_idx ON touchpoints (conversion_id, ts);
"""

PATHS_SQL = """
SELECT c.conversion_id, c.revenue, c.converted_at, t.channel, t.ts
FROM conversions c
JOIN touchpoints t ON t.conversion_id = c.conversion_id
ORDER BY c.conversion_id, t.ts
"""


class Warehouse:
    """A DuckDB file (or in-memory database) with the marketing schema."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = duckdb.connect(str(path))
        self._connection.execute(SCHEMA)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> Warehouse:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def record_spend(self, channel: str, day: str, amount: float) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO spend VALUES (?, ?, ?)", [channel, day, amount]
        )

    def record_conversion(
        self,
        *,
        conversion_id: str,
        user_id: str,
        revenue: float,
        converted_at: datetime,
        touchpoints: list[tuple[str, datetime]],
    ) -> None:
        """Insert one conversion and its ordered touchpoint list atomically."""
        self._connection.execute("BEGIN")
        try:
            self._connection.execute(
                "INSERT INTO conversions VALUES (?, ?, ?, ?)",
                [conversion_id, user_id, revenue, converted_at],
            )
            self._connection.executemany(
                "INSERT INTO touchpoints VALUES (?, ?, ?)",
                [[conversion_id, channel, ts] for channel, ts in touchpoints],
            )
        except BaseException:
            self._connection.execute("ROLLBACK")
            raise
        self._connection.execute("COMMIT")

    def conversion_count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) FROM conversions").fetchone()
        return int(row[0]) if row is not None else 0

    def paths(self) -> Iterator[ConversionPath]:
        """Stream every conversion with its ordered touchpoints."""
        rows = self._connection.execute(PATHS_SQL).fetchall()
        current_id: str | None = None
        revenue = 0.0
        converted_at = datetime.min
        touches: list[Touchpoint] = []

        def flush() -> ConversionPath:
            return ConversionPath(
                conversion_id=str(current_id),
                revenue=float(revenue),
                converted_at=converted_at,
                touchpoints=tuple(touches),
            )

        for conversion_id, conv_revenue, conv_ts, channel, ts in rows:
            if current_id is not None and conversion_id != current_id:
                yield flush()
                touches = []
            current_id = conversion_id
            revenue = float(conv_revenue)
            converted_at = conv_ts
            touches.append(Touchpoint(channel=str(channel), ts=ts))
        if current_id is not None:
            yield flush()

    def spend(self) -> dict[str, float]:
        """Channel -> total spend, the denominator for every RoI number."""
        rows = self._connection.execute("SELECT channel, SUM(amount) FROM spend GROUP BY channel").fetchall()
        return {str(channel): float(total) for channel, total in rows}
