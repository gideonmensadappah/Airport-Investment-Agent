export type AirportResult = {
  code: string;
  name: string;
  city: string;
  state: string;
  region: string;
  score: number;
  score_label: "congestion" | "expansion_opportunity";
  metrics: {
    average_departure_delay_minutes: number | null;
    cancellation_rate_pct: number | null;
    demand_growth_pct: number | null;
    capacity_pressure_pct: number | null;
    long_haul_share_pct: number | null;
  };
  component_scores: {
    demand_growth: number | null;
    congestion: number | null;
    capacity_pressure: number | null;
    long_haul_opportunity: number | null;
  };
};

export type DemandOpportunity = {
  destination: string;
  total_passengers: number;
  nonstop_passengers: number;
  connecting_passengers: number;
  connecting_share: number;
  average_connections: number | null;
  average_itinerary_distance: number | null;
  score: number;
};

export type SourceInfo = {
  name: string;
  period: string;
  scope: string;
  url: string | null;
};

type SharedChatResponse = {
  conversation_id: string;
  title: string;
  answer: string;
  confidence: "low" | "medium" | "high";
  assumptions: string[];
  limitations: string[];
  sources: SourceInfo[];
  methodology: string;
};

export type CongestionChatResponse = SharedChatResponse & {
  tool: "compare_congestion";
  results: AirportResult[];
  origin: null;
};

export type RankingChatResponse = SharedChatResponse & {
  tool: "rank_expansion_candidates";
  results: AirportResult[];
  origin: null;
};

export type DemandChatResponse = SharedChatResponse & {
  tool: "analyze_unmet_demand";
  results: DemandOpportunity[];
  origin: string;
};

export type ChatResponse =
  | CongestionChatResponse
  | RankingChatResponse
  | DemandChatResponse;

const supportedTools = new Set<ChatResponse["tool"]>([
  "compare_congestion",
  "rank_expansion_candidates",
  "analyze_unmet_demand",
]);

export function isChatResponse(value: unknown): value is ChatResponse {
  if (typeof value !== "object" || value === null) return false;

  const candidate = value as Record<string, unknown>;
  return typeof candidate.conversation_id === "string"
    && typeof candidate.tool === "string"
    && supportedTools.has(candidate.tool as ChatResponse["tool"])
    && Array.isArray(candidate.results);
}
