import unittest

from pydantic import ValidationError

from app.models.tool_calls import (
    AnalyzeUnmetDemandArguments,
    AnalyzeUnmetDemandToolCall,
    ClarificationDecision,
    CompareCongestionArguments,
    CompareCongestionToolCall,
    RankExpansionCandidatesToolCall,
)
from app.services.airport_resolver import AirportResolver
from app.services.intent_router import IntentRouter


class IntentRouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        resolver = AirportResolver(
            supported_codes={"LAX", "SFO", "SNA", "BOS", "BDL", "PVD", "MHT", "PWM"},
            supported_regions={"West", "New England"},
        )
        cls.router = IntentRouter(resolver)

    def test_routes_alternative_nonstop_opportunity_wording(self) -> None:
        decision = self.router.route("Find potential nonstop routes from Los Angeles.")

        self.assertIsInstance(decision, AnalyzeUnmetDemandToolCall)
        self.assertEqual(decision.arguments.airport, "LAX")

    def test_routes_congestion_and_preserves_airport_order(self) -> None:
        decision = self.router.route("Compare delays at SFO and LAX.")

        self.assertIsInstance(decision, CompareCongestionToolCall)
        self.assertEqual(decision.arguments.airports, ["SFO", "LAX"])

    def test_routes_supported_expansion_region(self) -> None:
        decision = self.router.route("Rank New England expansion candidates.")

        self.assertIsInstance(decision, RankExpansionCandidatesToolCall)
        self.assertEqual(decision.arguments.region, "New England")

    def test_requests_origin_for_demand_analysis(self) -> None:
        decision = self.router.route("Show potential nonstop opportunities.")

        self.assertIsInstance(decision, ClarificationDecision)
        self.assertIn("origin airport", decision.message)

    def test_requests_second_airport_for_congestion(self) -> None:
        decision = self.router.route("Show LAX congestion.")

        self.assertIsInstance(decision, ClarificationDecision)
        self.assertIn("at least two airports", decision.message)

    def test_tool_arguments_normalize_and_validate_iata_codes(self) -> None:
        demand = AnalyzeUnmetDemandArguments(airport=" lax ")
        self.assertEqual(demand.airport, "LAX")

        with self.assertRaises(ValidationError):
            CompareCongestionArguments(airports=["LAX", "LAX"])


if __name__ == "__main__":
    unittest.main()
