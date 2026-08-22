import type { ChatResponse } from "../types/analysis";

type AnalysisDetailsProps = Pick<
  ChatResponse,
  "assumptions" | "limitations" | "sources"
>;

export function AnalysisDetails({
  assumptions,
  limitations,
  sources,
}: AnalysisDetailsProps) {
  return (
    <>
      <div className="detail-grid">
        <section>
          <h3><span>◎</span> Assumptions</h3>
          <ul>{assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
        <section>
          <h3><span>◫</span> Limitations</h3>
          <ul>{limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      </div>

      {sources.map((source) => (
        <div className="source" key={source.name}>
          <span><i>↗</i><strong>{source.name}</strong> · {source.period}</span>
        </div>
      ))}
    </>
  );
}
