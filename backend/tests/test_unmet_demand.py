import unittest

from app.services.demand import DemandService


class UnmetDemandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = DemandService()

    def test_returns_ranked_lax_opportunities(self) -> None:
        results = self.service.get_unmet_demand(
            airport="LAX",
            top_n=5,
        )

        self.assertEqual(len(results), 5)
        self.assertEqual(results[0].destination, "SJU")

        scores = [result.score for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

        for result in results:
            self.assertGreaterEqual(result.score, 0)
            self.assertLessEqual(result.score, 100)
            self.assertGreaterEqual(result.connecting_share, 0)
            self.assertLessEqual(result.connecting_share, 1)

    def test_respects_top_n(self) -> None:
        results = self.service.get_unmet_demand(
            airport="SFO",
            top_n=3,
        )

        self.assertEqual(len(results), 3)

    def test_rejects_invalid_airport_code(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "three-letter IATA code",
        ):
            self.service.get_unmet_demand("Los Angeles")

    def test_rejects_non_positive_top_n(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "top_n must be positive",
        ):
            self.service.get_unmet_demand(
                airport="LAX",
                top_n=0,
            )


if __name__ == "__main__":
    unittest.main()