export function formatNumber(value: number | null, suffix = "") {
  return value === null ? "Unavailable" : `${value.toLocaleString()}${suffix}`;
}

export function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}
