import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_compares_lax_and_santa_ana_end_to_end(self) -> None:
        response = self.client.post(
            "/api/v1/chat",
            json={"message": "Compare LAX and Santa Ana airport congestion."},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tool"], "compare_congestion")
        self.assertEqual({item["code"] for item in payload["results"]}, {"LAX", "SNA"})
        self.assertEqual(payload["confidence"], "low")
        self.assertTrue(payload["assumptions"])
        self.assertTrue(payload["limitations"])
        self.assertEqual(payload["sources"][0]["name"], "Bundled MVP airport metrics")

    def test_health_confirms_the_data_snapshot_is_ready(self) -> None:
        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "data": "ready"})

    def test_allows_the_local_frontend_origin(self) -> None:
        response = self.client.options(
            "/api/v1/chat",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:5173",
        )

    def test_reuses_conversation_id(self) -> None:
        response = self.client.post(
            "/api/v1/chat",
            json={
                "message": "Compare SFO and LAX congestion.",
                "conversation_id": "demo-conversation",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["conversation_id"], "demo-conversation")

    def test_analyzes_lax_unmet_demand_end_to_end(self) -> None:
        response = self.client.post(
            "/api/v1/chat",
            json={"message": "Show unmet demand from LAX."},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tool"], "analyze_unmet_demand")
        self.assertEqual(payload["origin"], "LAX")
        self.assertEqual(len(payload["results"]), 5)
        self.assertEqual(payload["results"][0]["destination"], "SJU")
        self.assertTrue(payload["answer"])
        self.assertTrue(payload["assumptions"])
        self.assertTrue(payload["limitations"])
        self.assertEqual(payload["sources"][0]["name"], "US DOT DB1C Market dataset")

    def test_accepts_alternative_nonstop_opportunity_wording(self) -> None:
        response = self.client.post(
            "/api/v1/chat",
            json={"message": "Find potential nonstop routes from Los Angeles."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tool"], "analyze_unmet_demand")
        self.assertEqual(response.json()["origin"], "LAX")

    def test_requests_origin_for_unmet_demand(self) -> None:
        response = self.client.post(
            "/api/v1/chat",
            json={"message": "Show unmet demand opportunities."},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("origin airport", response.json()["detail"])

    def test_ranks_new_england_expansion_candidates_end_to_end(self) -> None:
        response = self.client.post(
            "/api/v1/chat",
            json={"message": "Rank New England airports."},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tool"], "rank_expansion_candidates")
        self.assertEqual(len(payload["results"]), 5)
        self.assertEqual(
            {result["code"] for result in payload["results"]},
            {"BOS", "BDL", "PVD", "MHT", "PWM"},
        )
        self.assertTrue(
            all(
                result["score_label"] == "expansion_opportunity"
                for result in payload["results"]
            )
        )
        scores = [result["score"] for result in payload["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(payload["methodology"])


if __name__ == "__main__":
    unittest.main()
