# Airport Investment Intelligence Agent

*Short Design & Architecture Document*
*Forward Deployed Engineer Take-Home Assignment*

> **Design principle:** The LLM decides which analysis to run; deterministic services calculate the metrics and scores.

# 1. Solution Overview

The Airport Investment Intelligence Agent is a conversational decision-support tool for analysts screening US airports for modernization or terminal-expansion opportunities. It gathers public airport and aviation data, calculates reproducible KPIs, ranks or compares airports, and explains the result together with its assumptions and uncertainty.

The MVP is an opportunity-screening tool, not a complete investment valuation. It does not estimate construction cost, financing, land availability, regulatory approval, or commercial revenue. These factors would be required before making a real investment decision.

# 2. Scope

* Resolve airport names, cities, regions, and IATA codes.

* Retrieve airport, flight, traffic, and route data from public sources.

* Compare two or more airports using deterministic KPIs.

* Rank airports in a geographic region by expansion-opportunity score.

* Calculate the percentage of long-haul departures when route data is available.

* Estimate an unmet-demand signal while clearly labeling it as a proxy.

* Support conversational follow-up questions such as ‘Why?’ or ‘Compare it with Boston.’

# 3. High-Level Architecture

The system separates conversational reasoning from data retrieval and numerical analysis. The chat interface sends each request to the backend, where the agent selects a typed tool. Data adapters retrieve and normalize public aviation data, and deterministic services calculate the requested metric or ranking. The LLM then explains the structured result without changing it.

| Component | Responsibility |
| --- | --- |
| Chat interface | Collects questions and displays answers, KPI breakdowns, sources, assumptions, and limitations. |
| Agent orchestrator | Understands intent, resolves conversational context, selects tools, and asks for clarification when needed. |
| Airport tools | Expose typed operations for metrics, comparison, ranking, long-haul percentage, and unmet-demand estimation. |
| Data adapters | Call public aviation sources and transform provider-specific responses into a common internal model. |
| Scoring engine | Calculates normalized KPI components and deterministic rankings. |
| Conversation state | Stores previously discussed airports, region, metric, and period for follow-up questions. |

## Deployment Topology

The free demo deployment keeps static delivery separate from backend compute:

```text
Browser
  -> Render Static Site (React/Vite CDN)
  -> Render Free Web Service (Dockerized FastAPI)
       -> immutable SQLite demand snapshot
       -> bundled airport metrics
       -> optional AeroDataBox enrichment
```

The separation keeps the interface available while Render's free API instance
is asleep. The frontend receives the API's generated public URL at build time,
and the API permits only the generated frontend origin through CORS. Both
services are declared in the repository's `render.yaml` Blueprint.

Docker packages only the API. Static assets remain in Render's CDN instead of
being coupled to the API lifecycle.

## Data Lifecycle

The multi-gigabyte DB1C source file is an offline pipeline input, not a runtime
dependency. `backend/scripts/build_airport_database.py` validates, aggregates,
and records provenance before producing the much smaller
`data/airport_data.db` read model. The generated snapshot is versioned with the
application and copied into the API image.

Runtime connections use SQLite read-only immutable mode. No user or application
state is written to the container filesystem, so Render's ephemeral free-tier
filesystem does not create a durability requirement. A future product that
needs mutable shared data should introduce a managed database rather than make
the container-local SQLite file writable.

# 4. Agent Workflow

1. Interpret the user’s request and determine whether it requires metrics, comparison, ranking, or clarification.

1. Resolve referenced locations into canonical airport codes and preserve relevant conversation context.

1. Call the appropriate typed tool; the LLM cannot query arbitrary URLs or create its own score.

1. Retrieve and normalize the required public aviation data.

1. Run deterministic calculations and return a structured result with sources, dates, missing fields, and confidence.

1. Use the LLM to explain the result in analyst-friendly language without modifying calculated values.

# 5. Deterministic Scoring Methodology

The Expansion Opportunity Score is a transparent screening score from 0 to 100.
Each component is normalized using fixed MVP reference bounds,
independently of the airport included in the current comparison.

For example, LAX receives the same normalized component scores whether it is compared with SNA or SFO.

```text
Opportunity Score =
0.35 × Demand Growth
+ 0.30 × Congestion
+ 0.25 × Capacity Pressure
+ 0.10 × Long-Haul Opportunity
```

```text
normalized = clamp((value - lower_bound) / (upper_bound - lower_bound), 0, 1) × 100
```

The reference bounds are fixed so that an airport's normalized score does not
change when the comparison group changes. They are intentionally wider than
the values in the bundled eight-airport dataset, leaving headroom below and
above the current sample instead of assigning 0 and 100 to the sample minimum
and maximum. These bounds are heuristic MVP calibration choices, not validated
aviation-industry thresholds. A production version should recalibrate them on
a larger historical dataset and test the ranking's sensitivity to each bound.

If any component is missing, the available weights are proportionally
renormalized:

```text
final score = sum(available component score × original weight) / sum(available weights)
```

| Input | Bounds | Usage |
|---|---:|---|
| Demand growth | ‎-2%–12% | 35% of Opportunity Score |
| Departure delay | 0–30 minutes | 70% of Congestion Score |
| Cancellation rate | 0%–5% | 30% of Congestion Score |
| Capacity pressure | 60%–95% | 25% of Opportunity Score |
| Long-haul share | 0%–30% | 10% of Opportunity Score |

Weight rationale:

- Demand Growth receives 35% because sustained market growth is the primary
  signal that additional airport capacity may be needed.
- Congestion receives 30% because current delays and cancellations indicate
  operational pressure that already exists.
- Capacity Pressure receives 25% because it complements demand and congestion
  by representing how constrained the existing facility may be.
- Long-Haul Opportunity receives 10% because network potential is useful as a
  supporting signal, but it cannot justify infrastructure investment by itself.
- Within the Congestion Score, departure delay receives 70% because it is a
  broader and more frequent operational signal. Cancellation rate receives 30%
  because cancellations are severe but less frequent and can also be driven by
  airline decisions or weather.

The weights express transparent expert judgment for MVP screening. They were
not learned from historical investment returns and should not be interpreted as
a validated profitability model.


Unmet demand formula:
```text
70% × min(connecting passengers / 3,000, 1) × 100 + 30% × connecting share × 100
```

The 3,000-passenger reference is an MVP saturation point that prevents raw
passenger volume from increasing the score without limit. It is not proof that
a route is commercially viable and should be recalibrated for the source period
and market size in a production analysis.

```text
Congestion Score =
70% normalized departure delay +
30% normalized cancellation rate
```


Demand Growth:
Bundled MVP demand-growth input, normalized from -2% to 12%.

Congestion:
Composite of normalized departure delay (70%) and cancellation rate (30%).

Capacity Pressure:
Bundled MVP capacity-pressure proxy. It is not measured terminal design capacity.

Long-Haul Opportunity:
Bundled MVP long-haul-share input representing the share of departures
over the defined 3,000-mile threshold.


Missing data: The system never invents a metric. If a component is unavailable, the score is calculated from the supported components using proportionally renormalized weights. The response identifies the missing component.

Current confidence behavior:
- High: all compared airports use AeroDataBox operational data.
- Medium: only some compared airports use AeroDataBox operational data.
- Low: no compared airport uses AeroDataBox operational data.

Known limitation / TODO:
Confidence does not yet account for component completeness.

Note:
Confidence is reported separately so users can distinguish score magnitude from data completeness.

# 6. Supporting KPI Definitions

Long-haul percentage = long-haul departures / departures with a known destination x 100. The response states the distance threshold, observation period, sample size, and coverage.

Unmet demand is not directly observable from public flight activity alone. The MVP therefore reports an Unmet Demand Signal based on DB1C and on 70% connecting-passenger volume
+ 30% connecting-passenger share. It is explicitly described as a screening proxy rather than the number of passengers who were unable to travel.

# 7. Where and How AI Is Used

| AI is used for | AI is not used for |
| --- | --- |
| Understanding natural-language questions | Inventing airport or flight data |
| Selecting the appropriate typed tool | Calculating KPI values or ranking scores |
| Resolving conversational follow-ups | Replacing missing data |
| Identifying ambiguity and requesting clarification | Changing deterministic tool results |
| Explaining results and limitations | Making a final investment decision |

# 8. Assumptions, Uncertainty, and Scoping

* Public sources may differ in reporting period, coverage, and update frequency; every result includes its source and observation period.

* Airport congestion is represented by available operational proxies rather than direct terminal occupancy.

* Long-haul is defined as at least 3,000 great-circle miles for this MVP and can be configured.

* An opportunity score supports prioritization but does not establish project profitability.

* When an airport reference is ambiguous, the agent asks the user to clarify instead of silently selecting an airport.

* Partial data is represented by unavailable component values.
Making confidence account for component completeness is a known MVP limitation.

# 9. Key Trade-offs

| Decision | Trade-off |
| --- | --- |
| Deterministic scoring | Produces reproducible and testable rankings, but requires explicit and potentially debatable weights. |
| LLM limited to orchestration | Reduces hallucination risk and improves traceability, but provides less open-ended autonomy. |
| Multiple public data sources | Improves metric coverage, but introduces inconsistent schemas, periods, and availability. |
| Proxy for unmet demand | Makes the use case achievable with public data, but cannot represent true suppressed passenger demand. |
| Conversation state in the MVP | Supports follow-up questions with minimal complexity, but is not designed for durable multi-user storage. |
| Clarity over completeness | Prioritizes a defensible working workflow over production-scale infrastructure or broad aviation coverage. |

# 10. Failure Handling

* External API failure: apply a timeout, retry once where appropriate, and return a partial or unavailable result rather than fabricated data.

* Missing metric: omit the metric, adjust the deterministic calculation according to the documented rule.

* Ambiguous airport: ask a clarification question.

* Agent loop: cap tool iterations and validate every tool argument.

# 11. MVP Deliverable

The implementation will provide a chat interface, an agent with typed tools, public aviation-data integration, deterministic comparison/ranking logic, conversational follow-ups, and visible assumptions and uncertainty. Voice, persistent enterprise storage, advanced observability, and full investment valuation remain outside the take-home scope.
