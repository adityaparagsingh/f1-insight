"""Entity extractors for the Jolpica F1 API.

Every function yields *raw* API dicts (lightly annotated with the parent race
context under ``_race``); all cleaning happens in the transform layer.
"""
from __future__ import annotations

from typing import Iterator, Optional

from etl.extract.client import JolpicaClient, page_items

# Immutable historical pages are cached forever; live/current data gets 30 min.
HISTORICAL_TTL = None
LIVE_TTL = 1800.0


class F1Api:
    def __init__(self, client: Optional[JolpicaClient] = None) -> None:
        self.client = client or JolpicaClient()

    # ------------------------------------------------------------- reference
    def races(self, season: Optional[int] = None) -> Iterator[dict]:
        path = f"{season}/races.json" if season else "races.json"
        for page in self.client.iter_pages(path):
            yield from page_items(page, "Races")

    def drivers(self, season: Optional[int] = None) -> Iterator[dict]:
        path = f"{season}/drivers.json" if season else "drivers.json"
        for page in self.client.iter_pages(path):
            yield from page_items(page, "Drivers")

    def constructors(self, season: Optional[int] = None) -> Iterator[dict]:
        path = f"{season}/constructors.json" if season else "constructors.json"
        for page in self.client.iter_pages(path):
            yield from page_items(page, "Constructors")

    def circuits(self) -> Iterator[dict]:
        for page in self.client.iter_pages("circuits.json"):
            yield from page_items(page, "Circuits")

    # ------------------------------------------------------------- facts
    def results(self, season: Optional[int] = None) -> Iterator[dict]:
        path = f"{season}/results.json" if season else "results.json"
        for page in self.client.iter_pages(path):
            yield from page_items(page, "Results")

    def qualifying(self, season: Optional[int] = None) -> Iterator[dict]:
        path = f"{season}/qualifying.json" if season else "qualifying.json"
        for page in self.client.iter_pages(path):
            yield from page_items(page, "QualifyingResults")

    def pit_stops(self, season: int, round_: int) -> Iterator[dict]:
        path = f"{season}/{round_}/pitstops.json"
        for page in self.client.iter_pages(path):
            yield from page_items(page, "PitStops")

    def laps(self, season: int, round_: int) -> Iterator[dict]:
        """Yield driver-lap rows: {'lap', 'driverId', 'position', 'time', _race}."""
        path = f"{season}/{round_}/laps.json"
        for page in self.client.iter_pages(path):
            races = (page.get("RaceTable") or {}).get("Races") or []
            for race in races:
                race_ctx = {
                    "season": race.get("season"),
                    "round": race.get("round"),
                    "raceName": race.get("raceName"),
                    "date": race.get("date"),
                    "url": race.get("url"),
                    "Circuit": race.get("Circuit"),
                }
                for lap_group in race.get("Laps") or []:
                    lap_no = lap_group.get("number")
                    for timing in lap_group.get("Timings") or []:
                        yield {
                            "lap": lap_no,
                            "driverId": timing.get("driverId"),
                            "position": timing.get("position"),
                            "time": timing.get("time"),
                            "_race": race_ctx,
                        }

    # ------------------------------------------------------------ standings
    def driver_standings(self, season: int, round_: int) -> Iterator[dict]:
        path = f"{season}/{round_}/driverstandings.json"
        data = self.client.get(path, ttl=HISTORICAL_TTL)
        yield from _standings_rows(data, "DriverStandings", season, round_)

    def constructor_standings(self, season: int, round_: int) -> Iterator[dict]:
        path = f"{season}/{round_}/constructorstandings.json"
        data = self.client.get(path, ttl=HISTORICAL_TTL)
        yield from _standings_rows(data, "ConstructorStandings", season, round_)

    def season_driver_standings(self, season: int) -> Iterator[dict]:
        """Final (end-of-season) driver standings for a season."""
        path = f"{season}/driverstandings.json"
        data = self.client.get(path, ttl=HISTORICAL_TTL)
        yield from _standings_rows(data, "DriverStandings", season, 0)

    def season_constructor_standings(self, season: int) -> Iterator[dict]:
        path = f"{season}/constructorstandings.json"
        data = self.client.get(path, ttl=HISTORICAL_TTL)
        yield from _standings_rows(data, "ConstructorStandings", season, 0)


def _standings_rows(data: dict, key: str, season: int, round_: int) -> Iterator[dict]:
    table = data.get("MRData", {}).get("StandingsTable") or {}
    for lst in table.get("StandingsLists") or []:
        for row in lst.get(key) or []:
            yield {
                **row,
                "_season": season,
                "_round": int(lst.get("round") or round_ or 0),
                "_table_season": table.get("season"),
            }
