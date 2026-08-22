import re


AIRPORT_ALIASES = {
    "los angeles": "LAX",
    "la": "LAX",
    "santa ana": "SNA",
    "john wayne": "SNA",
    "san francisco": "SFO",
    "boston": "BOS",
    "hartford": "BDL",
    "providence": "PVD",
    "manchester": "MHT",
    "portland": "PWM",
}


class AirportResolver:
    def __init__(self, supported_codes: set[str], supported_regions: set[str]) -> None:
        self.supported_codes = {code.upper() for code in supported_codes}
        self.supported_regions = supported_regions

    def extract_airports(self, message: str) -> list[str]:
        found: list[tuple[int, str]] = []

        for alias, code in AIRPORT_ALIASES.items():
            match = re.search(rf"\b{re.escape(alias)}\b", message, flags=re.IGNORECASE)
            if match and code in self.supported_codes:
                found.append((match.start(), code))

        for match in re.finditer(r"\b[A-Za-z]{3}\b", message):
            code = match.group().upper()
            if code in self.supported_codes:
                found.append((match.start(), code))

        ordered: list[str] = []
        for _, code in sorted(found):
            if code not in ordered:
                ordered.append(code)
        return ordered

    def extract_region(self, message: str) -> str | None:
        for region in sorted(self.supported_regions, key=len, reverse=True):
            if re.search(rf"\b{re.escape(region)}\b", message, flags=re.IGNORECASE):
                return region
        return None
