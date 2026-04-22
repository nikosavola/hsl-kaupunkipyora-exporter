"""Parse HSL City Bike ride history from saved HTML or plain-text files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import ClassVar, final, override

from bs4 import BeautifulSoup


@dataclass(slots=True)
class Ride:
    """A single bike ride extracted from the history page."""

    departure_station: str
    departure_time: datetime
    return_station: str
    return_time: datetime
    distance_km: float | None = None
    duration_min: int | None = None

    @override
    def __str__(self) -> str:
        """Return a string representation of the ride."""
        s = (
            f"{self.departure_station} → {self.return_station} "
            f"({self.departure_time:%Y-%m-%d %H:%M} – {self.return_time:%H:%M})"
        )
        details = []
        if self.distance_km is not None:
            details.append(f"{self.distance_km} km")
        if self.duration_min is not None:
            details.append(f"{self.duration_min} min")
        if details:
            s += f" [{', '.join(details)}]"
        return s


@final
class RideHistoryParser:
    """Parser for HSL City Bike ride history files."""

    DATETIME_FMT = "%d.%m.%Y %H:%M"
    _MIN_LINES_FOR_SUMMARY = 6

    # Regex patterns for detail lines
    _FIELD_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        (
            re.compile(r"Departure\s+station:\s*(.+)", re.IGNORECASE),
            "departure_station",
        ),
        (re.compile(r"Departure\s+time:\s*(.+)", re.IGNORECASE), "departure_time"),
        (re.compile(r"Return\s+station:\s*(.+)", re.IGNORECASE), "return_station"),
        (re.compile(r"Return\s+time:\s*(.+)", re.IGNORECASE), "return_time"),
        (re.compile(r"Lähtöasema:\s*(.+)", re.IGNORECASE), "departure_station"),
        (re.compile(r"Lähtöaika:\s*(.+)", re.IGNORECASE), "departure_time"),
        (re.compile(r"Palautusasema:\s*(.+)", re.IGNORECASE), "return_station"),
        (re.compile(r"Palautusaika:\s*(.+)", re.IGNORECASE), "return_time"),
        (re.compile(r"Avgångsstation:\s*(.+)", re.IGNORECASE), "departure_station"),
        (re.compile(r"Starttid:\s*(.+)", re.IGNORECASE), "departure_time"),
        (re.compile(r"Återlämningss?tation:\s*(.+)", re.IGNORECASE), "return_station"),
        (re.compile(r"Återlämningstid:\s*(.+)", re.IGNORECASE), "return_time"),
        (re.compile(r"city-bikes/return-date:\s*(.+)", re.IGNORECASE), "return_time"),
        (
            re.compile(r"Journey\s+length\s+and\s+duration:\s*(.+)", re.IGNORECASE),
            "dist_dur",
        ),
        (
            re.compile(r"Matkan\s+pituus\s+ja\s+kesto:\s*(.+)", re.IGNORECASE),
            "dist_dur",
        ),
        (re.compile(r"Distans\s+och\s+tid:\s*(.+)", re.IGNORECASE), "dist_dur"),
    ]

    _TS_PATTERN = re.compile(r"\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2}")

    def parse_file(self, path: str | Path) -> list[Ride]:
        """Read file and return the rides it contains.

        Args:
            path: Path to the ride history file.

        Returns:
            A list of extracted Ride objects.
        """
        content = Path(path).read_text(encoding="utf-8")

        # Detect HTML or HTML fragments
        if re.search(r"<\s*(html|div|ul|li|p)[\s>]", content, re.IGNORECASE):
            return self.parse_html(content)
        return self.parse_text(content)

    def parse_html(self, html: str) -> list[Ride]:
        """Extract rides from a saved HTML file.

        Args:
            html: HTML content of the ride history page.

        Returns:
            A list of extracted Ride objects.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Try to find high-quality labeled data first (screen reader only sections)
        rides: list[Ride] = []
        seen_keys: set[tuple] = set()

        sr_elements = soup.find_all(
            class_=re.compile(r"screenReaderOnly", re.IGNORECASE)
        )
        if sr_elements:
            for el in sr_elements:
                text = el.get_text(separator="\n")
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                ride = self._parse_chunk(lines)
                if ride:
                    key = (
                        ride.departure_station,
                        ride.departure_time,
                        ride.return_station,
                        ride.return_time,
                    )
                    if key not in seen_keys:
                        rides.append(ride)
                        seen_keys.add(key)

        # Fallback to parsing the whole visible text if we found nothing
        # or to catch rides that might not have been in the SR blocks.
        visible_text = soup.get_text(separator="\n")
        visible_rides = self.parse_text(visible_text)

        for ride in visible_rides:
            key = (
                ride.departure_station,
                ride.departure_time,
                ride.return_station,
                ride.return_time,
            )
            if key not in seen_keys:
                rides.append(ride)
                seen_keys.add(key)

        return sorted(rides, key=lambda r: r.departure_time)

    def parse_text(self, text: str) -> list[Ride]:
        """Extract rides from a plain-text copy of the ride history page.

        Args:
            text: Text content of the ride history page.

        Returns:
            A list of extracted Ride objects.
        """
        # Split into chunks based on common separators
        chunks = re.split(
            r"(?:Vikailmoitus|Fault report|Felanmälan)(?:\s*[›>])?|(?=Departure\s+station:|Lähtöasema:|Avgångsstation:)",
            text,
            flags=re.IGNORECASE,
        )

        all_rides: list[Ride] = []
        seen_keys: set[tuple] = set()

        for chunk in chunks:
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            if not lines:
                continue

            ride = self._parse_chunk(lines)
            if ride:
                key = (
                    ride.departure_station,
                    ride.departure_time,
                    ride.return_station,
                    ride.return_time,
                )
                if key not in seen_keys:
                    all_rides.append(ride)
                    seen_keys.add(key)

        return sorted(all_rides, key=lambda r: r.departure_time)

    def _parse_chunk(self, lines: list[str]) -> Ride | None:
        """Try to parse a ride from a list of lines.

        Args:
            lines: List of lines in a potential ride chunk.

        Returns:
            A Ride object if parsing succeeded, else None.
        """
        # 1. Label-based parsing
        fields: dict[str, str] = {}
        for line in lines:
            result = self._match_field(line)
            if result:
                name, value = result
                fields[name] = value

        ride = self._build_ride(fields)
        if ride:
            return ride

        # 2. Positional/summary parsing fallback
        # We look for a pattern of:
        # Station Name
        # Time
        # Distance (X,Y km)
        # Duration (X min)
        # Return Station Name
        # Return Time
        # (This matches the visible HTML summary format)
        for i in range(len(lines) - 5):
            if self._TS_PATTERN.match(lines[i + 1]) and self._TS_PATTERN.match(
                lines[i + 5]
            ):
                fields = {
                    "departure_station": lines[i],
                    "departure_time": lines[i + 1],
                    "dist_dur": f"{lines[i + 2]}, {lines[i + 3]}",
                    "return_station": lines[i + 4],
                    "return_time": lines[i + 5],
                }
                ride = self._build_ride(fields)
                if ride:
                    return ride

        return None

    def _match_field(self, line: str) -> tuple[str, str] | None:
        """Return (field_name, value) if line matches a known detail field.

        Args:
            line: A single line of text.

        Returns:
            A tuple of (field_name, value) if matched, else None.
        """
        for pattern, name in self._FIELD_PATTERNS:
            if (m := pattern.match(line.strip())):
                return name, m.group(1).strip()
        return None

    def _build_ride(self, fields: dict[str, str]) -> Ride | None:
        """Construct a Ride from a dict of raw string values.

        Args:
            fields: Dictionary of raw field values.

        Returns:
            A Ride object if construction succeeded, else None.
        """
        try:
            ride = Ride(
                departure_station=fields["departure_station"],
                departure_time=datetime.strptime(
                    fields["departure_time"], self.DATETIME_FMT
                ),
                return_station=fields["return_station"],
                return_time=datetime.strptime(fields["return_time"], self.DATETIME_FMT),
            )

            if "dist_dur" in fields:
                val = fields["dist_dur"]
                dist_match = re.search(r"(\d+([.,]\d+)?)\s*km", val)
                if dist_match:
                    ride.distance_km = float(dist_match.group(1).replace(",", "."))

                dur_match = re.search(r"(\d+)\s*min", val)
                if dur_match:
                    ride.duration_min = int(dur_match.group(1))
        except (KeyError, ValueError):
            return None
        else:
            return ride
