import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_airport_database import build_database

from app.services.demand import DemandService


class AirportDatabaseTests(unittest.TestCase):
    def test_builds_aggregated_database_and_queries_any_origin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "demand.csv"
            database = root / "airport.db"
            metrics = root / "metrics.json"
            source.write_text(
                "MktCoupons,Origin,Dest,Passengers,TotalDistance,NonStopMiles,Nonstop\n"
                "1,SFO,JFK,10,2586,2586,1\n"
                "1,SFO,JFK,5,2586,2586,1\n"
                "2,SFO,JFK,20,3000,2586,0\n"
                "3,SFO,JFK,10,3500,2586,0\n"
                "2,LAX,BOS,7,2800,2611,0\n"
                "2,?,BOS,99,2800,2611,0\n",
                encoding="utf-8",
            )
            metrics.write_text(
                json.dumps(
                    [
                        {
                            "code": "SFO", "name": "San Francisco International Airport",
                            "city": "San Francisco", "state": "CA", "region": "West",
                            "average_departure_delay_minutes": 20,
                            "cancellation_rate_pct": 2, "demand_growth_pct": 5,
                            "capacity_pressure_pct": 80, "long_haul_share_pct": 20,
                        }
                    ]
                ),
                encoding="utf-8",
            )

            stats = build_database(source, database, metrics, chunk_size=2)
            service = DemandService(database_file=database)
            result = service.get_unmet_demand("SFO")

            self.assertEqual(stats["rows_read"], 6)
            self.assertEqual(stats["rows_rejected"], 1)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].destination, "JFK")
            self.assertEqual(result[0].total_passengers, 45)
            self.assertEqual(result[0].nonstop_passengers, 15)
            self.assertEqual(result[0].connecting_passengers, 30)
            self.assertAlmostEqual(result[0].connecting_share, 2 / 3)
            self.assertAlmostEqual(result[0].average_connections, 4 / 3)
            self.assertAlmostEqual(result[0].average_itinerary_distance, 133790 / 45)

            lax_result = service.get_unmet_demand("LAX")
            self.assertEqual(lax_result[0].destination, "BOS")


if __name__ == "__main__":
    unittest.main()
