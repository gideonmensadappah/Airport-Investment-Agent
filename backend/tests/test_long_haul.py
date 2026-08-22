import unittest

from app.services.long_haul import LongHaulService, great_circle_miles


class FakeAeroDataBoxClient:
    configured = True

    def get_airport_metadata(self, code: str) -> dict:
        raise AssertionError("ANC snapshot coordinates should avoid a second API call")

    def get_daily_routes(self, code: str) -> dict:
        self.requested_code = code
        return {
            "routes": [
                {
                    "destination": {
                        "iata": "JFK",
                        "shortName": "New York JFK",
                        "location": {"lat": 40.6413, "lon": -73.7781},
                    },
                    "averageDailyFlights": 2.0,
                },
                {
                    "destination": {
                        "iata": "SEA",
                        "shortName": "Seattle Tacoma",
                        "location": {"lat": 47.4502, "lon": -122.3088},
                    },
                    "averageDailyFlights": 8.0,
                },
                {
                    "destination": {"iata": "UNK", "shortName": "Unknown"},
                    "averageDailyFlights": 2.0,
                },
            ]
        }


class LongHaulServiceTests(unittest.TestCase):
    def test_haversine_distance_matches_known_route(self) -> None:
        distance = great_circle_miles(61.1744, -149.996, 40.6413, -73.7781)

        self.assertAlmostEqual(distance, 3377, delta=5)

    def test_live_share_is_weighted_by_departure_frequency(self) -> None:
        client = FakeAeroDataBoxClient()
        service = LongHaulService(client)

        result = service.analyze_long_haul_share("anc")

        self.assertEqual(client.requested_code, "ANC")
        self.assertEqual(result.long_haul_share_pct, 20.0)
        self.assertEqual(result.long_haul_average_daily_flights, 2.0)
        self.assertEqual(result.known_distance_average_daily_flights, 10.0)
        self.assertEqual(result.total_average_daily_flights, 12.0)
        self.assertEqual(result.coverage_pct, 83.3)
        self.assertEqual(result.results[0].destination, "JFK")
        self.assertEqual(result.confidence, "medium")
        self.assertIn("AeroDataBox", result.sources[0].name)

    def test_bundled_snapshot_keeps_demo_available_without_api(self) -> None:
        client = FakeAeroDataBoxClient()
        client.configured = False
        service = LongHaulService(client, use_live_data=False)

        result = service.analyze_long_haul_share("ANC")

        self.assertEqual(result.long_haul_share_pct, 19.7)
        self.assertEqual(result.coverage_pct, 99.9)
        self.assertEqual(result.confidence, "medium")
        self.assertIn("snapshot", result.sources[0].name.lower())


if __name__ == "__main__":
    unittest.main()
