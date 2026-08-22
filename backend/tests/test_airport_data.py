import unittest

from app.models.analysis import AirportMetrics
from app.services.airport_data import AeroDataBoxClient, AirportRecord


class StubAeroDataBoxClient(AeroDataBoxClient):
    def __init__(self, metadata: dict, delays: dict) -> None:
        super().__init__(
            api_key="test-key",
            base_url="https://example.test",
            rapidapi_host="example.test",
        )
        self.metadata = metadata
        self.delays = delays

    def _safe_get(self, path: str) -> dict:
        return self.delays if path.endswith("/delays") else self.metadata


def airport_record() -> AirportRecord:
    return AirportRecord(
        code="LAX",
        name="Local Airport Name",
        city="Local City",
        state="CA",
        region="West",
        metrics=AirportMetrics(
            average_departure_delay_minutes=21.4,
            cancellation_rate_pct=2.1,
            demand_growth_pct=5.8,
            capacity_pressure_pct=88.0,
            long_haul_share_pct=23.0,
        ),
    )


class AeroDataBoxClientTests(unittest.TestCase):
    def test_uses_live_operational_bundle_when_both_metrics_are_available(self) -> None:
        client = StubAeroDataBoxClient(
            metadata={},
            delays={
                "departuresDelayInformation": {
                    "medianDelay": "00:18:00",
                    "numTotal": 100,
                    "numCancelled": 2,
                },
                "from": {"utc": "2026-08-22T10:00:00Z"},
                "to": {"utc": "2026-08-22T12:00:00Z"},
            },
        )

        enriched = client.enrich(airport_record())

        self.assertEqual(enriched.metrics.average_departure_delay_minutes, 18.0)
        self.assertEqual(enriched.metrics.cancellation_rate_pct, 2.0)
        self.assertEqual(enriched.operational_data_source, "aerodatabox")
        self.assertEqual(enriched.metadata_source, "local_fallback")
        self.assertEqual(
            enriched.observation_period,
            "2026-08-22T10:00:00Z to 2026-08-22T12:00:00Z",
        )

    def test_keeps_local_operational_bundle_when_live_response_is_partial(self) -> None:
        partial_payloads = (
            {
                "departuresDelayInformation": {
                    "medianDelay": "00:18:00",
                },
            },
            {
                "departuresDelayInformation": {
                    "numTotal": 100,
                    "numCancelled": 2,
                },
            },
        )

        for delays in partial_payloads:
            with self.subTest(delays=delays):
                original = airport_record()
                client = StubAeroDataBoxClient(
                    metadata={
                        "fullName": "Live Airport Name",
                        "municipalityName": "Live City",
                    },
                    delays=delays,
                )

                enriched = client.enrich(original)

                self.assertEqual(enriched.metrics, original.metrics)
                self.assertEqual(enriched.operational_data_source, "local_fallback")
                self.assertEqual(enriched.observation_period, original.observation_period)
                self.assertEqual(enriched.metadata_source, "aerodatabox")
                self.assertEqual(enriched.name, "Live Airport Name")
                self.assertEqual(enriched.city, "Live City")


if __name__ == "__main__":
    unittest.main()
