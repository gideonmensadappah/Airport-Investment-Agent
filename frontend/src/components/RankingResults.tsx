import type { RankingChatResponse } from "../types/analysis";
import { formatNumber } from "../utils/formatters";

type RankingResultsProps = {
  response: RankingChatResponse;
};

export function RankingResults({ response }: RankingResultsProps) {
  return (
    <section className="results-card">
      <header>
        <div>
          <small>Regional expansion ranking</small>
          <h2>Expansion opportunity</h2>
        </div>
        <span>Score / 100</span>
      </header>

      {response.results.map((airport, index) => (
        <div className="airport-row ranking-row" key={airport.code}>
          <div className="airport">
            <span className={`code code-${index}`}>{airport.code}</span>
            <div>
              <strong>{airport.name}</strong>
              <small>{airport.city}, {airport.state}</small>
            </div>
          </div>
          <ScoreDisplay code={airport.code} score={airport.score} />
          <ComponentScore label="Demand growth" value={airport.component_scores.demand_growth} />
          <ComponentScore label="Congestion" value={airport.component_scores.congestion} />
          <ComponentScore label="Capacity pressure" value={airport.component_scores.capacity_pressure} />
          <ComponentScore label="Long-haul" value={airport.component_scores.long_haul_opportunity} />
        </div>
      ))}

      <footer><span>ƒ</span><p>{response.methodology}</p></footer>
    </section>
  );
}

function ComponentScore({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="datum">
      <span>{label}</span>
      <strong>{formatNumber(value, "/100")}</strong>
    </div>
  );
}

function ScoreDisplay({ code, score }: { code: string; score: number }) {
  return (
    <div className="score">
      <strong>{score}</strong>
      <div aria-label={`${code} expansion opportunity score: ${score}`}>
        <span style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}
