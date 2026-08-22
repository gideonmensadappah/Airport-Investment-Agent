import type {
  ChatResponse,
  CongestionChatResponse,
  DemandChatResponse,
} from "../types/analysis";
import { formatNumber, formatPercent } from "../utils/formatters";
import { RankingResults } from "./RankingResults";

type AnalysisResultsProps = {
  response: ChatResponse;
};

export function AnalysisResults({ response }: AnalysisResultsProps) {
  if (response.tool === "analyze_unmet_demand") {
    return <DemandResults response={response} />;
  }
  if (response.tool === "rank_expansion_candidates") {
    return <RankingResults response={response} />;
  }
  return <CongestionResults response={response} />;
}

function DemandResults({ response }: { response: DemandChatResponse }) {
  return (
    <section className="results-card">
      <header>
        <div><small>Origin · {response.origin}</small><h2>Potential nonstop opportunities</h2></div>
        <span>Score / 100</span>
      </header>
      {response.results.map((opportunity, index) => (
        <div className="airport-row" key={opportunity.destination}>
          <div className="airport">
            <span className={`code code-${index}`}>{opportunity.destination}</span>
            <div>
              <strong>{formatNumber(opportunity.connecting_passengers, " connecting passengers")}</strong>
              <small>{formatPercent(opportunity.connecting_share)} connecting share</small>
            </div>
          </div>
          <div className="score">
            <strong>{opportunity.score}</strong>
            <div aria-label={`${opportunity.destination} score: ${opportunity.score}`}>
              <span style={{ width: `${opportunity.score}%` }} />
            </div>
          </div>
          <div className="datum">
            <span>Total passengers</span>
            <strong>{formatNumber(opportunity.total_passengers)}</strong>
          </div>
          <div className="datum">
            <span>Average connections</span>
            <strong>{formatNumber(opportunity.average_connections)}</strong>
          </div>
        </div>
      ))}
      <Methodology text={response.methodology} />
    </section>
  );
}

function CongestionResults({ response }: { response: CongestionChatResponse }) {
  return (
    <section className="results-card">
      <header>
        <div><small>Congestion comparison</small><h2>Operational pressure</h2></div>
        <span>Score / 100</span>
      </header>
      {response.results.map((airport, index) => (
        <div className="airport-row" key={airport.code}>
          <div className="airport">
            <span className={`code code-${index}`}>{airport.code}</span>
            <div><strong>{airport.name}</strong><small>{airport.city}, {airport.state}</small></div>
          </div>
          <div className="score">
            <strong>{airport.score}</strong>
            <div aria-label={`${airport.code} score: ${airport.score}`}>
              <span style={{ width: `${airport.score}%` }} />
            </div>
          </div>
          <div className="datum">
            <span>Departure delay</span>
            <strong>{formatNumber(airport.metrics.average_departure_delay_minutes, " min")}</strong>
          </div>
          <div className="datum">
            <span>Cancellation</span>
            <strong>{formatNumber(airport.metrics.cancellation_rate_pct, "%")}</strong>
          </div>
        </div>
      ))}
      <Methodology text={response.methodology} />
    </section>
  );
}

function Methodology({ text }: { text: string }) {
  return <footer><span>ƒ</span><p>{text}</p></footer>;
}
