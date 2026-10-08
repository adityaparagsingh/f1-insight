"""HTTP client for the Jolpica (Ergast-compatible) Formula 1 API.

Features
--------
* Rate limiting            — minimum interval between requests (RPS configurable)
* Retry / backoff          — exponential backoff with jitter on 429/5xx/timeouts,
                             honours ``Retry-After``
* Timeout handling          — per-request timeout
* Local disk cache          — raw JSON responses stored under ``ETL_CACHE_DIR``
                             keyed by URL+params; historical data cached
                             indefinitely (immutable), live data with TTL
* Pagination                — ``iter_pages`` walks limit/offset pages safely
                             (stops on empty pages and on ``total``)
* Error handling            — raises ``JolpicaError`` after exhausting retries
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

import requests

from app.config import (
    JOLPICA_BASE_URL,
    JOLPICA_MAX_RETRIES,
    JOLPICA_REQUESTS_PER_SECOND,
    JOLPICA_TIMEOUT,
    ETL_CACHE_DIR,
)
from etl.logging_utils import get_logger

log = get_logger("etl.extract")

PAGE_LIMIT = 100  # Jolpica/Ergast maximum page size


class JolpicaError(RuntimeError):
    """Raised when a request ultimately fails after retries."""


class JolpicaClient:
    def __init__(
        self,
        base_url: str = JOLPICA_BASE_URL,
        timeout: int = JOLPICA_TIMEOUT,
        max_retries: int = JOLPICA_MAX_RETRIES,
        requests_per_second: float = JOLPICA_REQUESTS_PER_SECOND,
        cache_dir: Optional[Path] = None,
        use_cache: bool = True,
        refresh_cache: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self.cache_dir = Path(cache_dir or ETL_CACHE_DIR)
        self.use_cache = use_cache
        self.refresh_cache = refresh_cache
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "F1-Insight-ETL/1.0 (college project)"})
        self._last_request_at = 0.0
        self.stats = {"requests": 0, "cache_hits": 0, "retries": 0, "errors": 0}

    # ------------------------------------------------------------------ cache
    def _cache_path(self, path: str, params: dict) -> Path:
        key = json.dumps({"u": path, "p": sorted(params.items())}, sort_keys=True)
        digest = hashlib.sha1(key.encode()).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, path: str, params: dict, ttl: Optional[float]) -> Optional[dict]:
        if not self.use_cache or self.refresh_cache:
            return None
        fp = self._cache_path(path, params)
        if not fp.exists():
            return None
        try:
            payload = json.loads(fp.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        if ttl is not None and (time.time() - payload.get("fetched_at", 0)) > ttl:
            return None
        return payload.get("response")

    def _write_cache(self, path: str, params: dict, response: dict) -> None:
        if not self.use_cache:
            return
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            fp = self._cache_path(path, params)
            tmp = fp.with_suffix(".tmp")
            tmp.write_text(json.dumps({"fetched_at": time.time(), "response": response}))
            tmp.replace(fp)
        except OSError as exc:  # pragma: no cover
            log.warning("cache write failed: %s", exc)

    # ---------------------------------------------------------------- request
    def _throttle(self) -> None:
        delta = time.monotonic() - self._last_request_at
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)

    def get(self, path: str, params: Optional[dict] = None, ttl: Optional[float] = None) -> dict:
        """GET a resource; returns parsed JSON (cache-first)."""
        params = dict(params or {})
        cached = self._read_cache(path, params, ttl)
        if cached is not None:
            self.stats["cache_hits"] += 1
            return cached

        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error: Optional[str] = None

        for attempt in range(self.max_retries):
            self._throttle()
            self._last_request_at = time.monotonic()
            self.stats["requests"] += 1
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 404:
                    # Endpoint has no data for this scope (e.g. pit stops for
                    # a classic-era race) — return an empty MRData payload.
                    log.info("404 for %s — treating as empty result set", url)
                    return {"MRData": {}}
                if resp.status_code == 429 or resp.status_code >= 500:
                    retry_after = resp.headers.get("Retry-After")
                    wait = (
                        float(retry_after)
                        if retry_after and retry_after.replace(".", "", 1).isdigit()
                        else min(2**attempt, 30) + random.uniform(0, 0.5)
                    )
                    last_error = f"HTTP {resp.status_code}"
                    log.warning(
                        "%s -> %s (attempt %d/%d, sleeping %.1fs)",
                        url, resp.status_code, attempt + 1, self.max_retries, wait,
                    )
                    self.stats["retries"] += 1
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, dict) or "MRData" not in data:
                    raise JolpicaError(f"Unexpected payload shape from {url}")
                self._write_cache(path, params, data)
                return data
            except (requests.Timeout, requests.ConnectionError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                wait = min(2**attempt, 30) + random.uniform(0, 0.5)
                log.warning(
                    "%s failed (%s) attempt %d/%d, sleeping %.1fs",
                    url, last_error, attempt + 1, self.max_retries, wait,
                )
                self.stats["retries"] += 1
                time.sleep(wait)

        self.stats["errors"] += 1
        raise JolpicaError(f"GET {url} failed after {self.max_retries} attempts: {last_error}")

    # ------------------------------------------------------------- pagination
    def iter_pages(
        self,
        path: str,
        params: Optional[dict] = None,
        ttl: Optional[float] = None,
        max_pages: Optional[int] = None,
    ) -> Iterator[dict]:
        """Yield each MRData page dict for a paginated endpoint.

        Walks ``offset`` by ``limit`` until ``total`` is reached, with a hard
        stop on empty pages (protects against endpoints whose ``total`` counts
        nested rows differently from page entries).
        """
        params = dict(params or {})
        offset = int(params.get("offset", 0))
        total: Optional[int] = None
        pages = 0
        seen_offsets: set[int] = set()

        while True:
            if offset in seen_offsets:  # defensive: never loop forever
                break
            seen_offsets.add(offset)
            page_params = {**params, "limit": PAGE_LIMIT, "offset": offset}
            data = self.get(path, page_params, ttl=ttl)
            mr = data["MRData"]
            yield mr
            pages += 1
            try:
                total = int(mr.get("total") or 0)
            except (TypeError, ValueError):
                total = 0
            limit = int(mr.get("limit") or PAGE_LIMIT) or PAGE_LIMIT
            offset += limit
            if max_pages is not None and pages >= max_pages:
                break
            if total and offset >= total:
                break
            # stop when this page contributed nothing
            if not _page_has_rows(mr):
                break


def _page_has_rows(mr: dict) -> bool:
    """Whether an MRData page carried any data rows."""
    rt = mr.get("RaceTable")
    if rt and rt.get("Races"):
        return True
    for table_key, list_key in (
        ("DriverTable", "Drivers"),
        ("ConstructorTable", "Constructors"),
        ("CircuitTable", "Circuits"),
    ):
        tbl = mr.get(table_key)
        if tbl and tbl.get(list_key):
            return True
    if mr.get("StandingsTable"):
        return True
    return False


def page_items(mr: dict, key: str) -> list[dict]:
    """Extract a list of rows from a page.

    Handles both shapes used by the Jolpica API:
      * ``RaceTable.Races[*][key]``  — results / qualifying / laps / pit stops
      * ``DriverTable|ConstructorTable|CircuitTable[key]`` — reference lists
    """
    if key == "Races":
        return list((mr.get("RaceTable") or {}).get("Races") or [])

    list_tables = {"Drivers": "DriverTable", "Constructors": "ConstructorTable",
                   "Circuits": "CircuitTable"}
    if key in list_tables:
        return list((mr.get(list_tables[key]) or {}).get(key) or [])

    races = (mr.get("RaceTable") or {}).get("Races") or []
    rows: list[dict] = []
    for race in races:
        for item in race.get(key) or []:
            row = dict(item)
            row["_race"] = {
                "season": race.get("season"),
                "round": race.get("round"),
                "raceName": race.get("raceName"),
                "date": race.get("date"),
                "time": race.get("time"),
                "url": race.get("url"),
                "Circuit": race.get("Circuit"),
            }
            rows.append(row)
    return rows
