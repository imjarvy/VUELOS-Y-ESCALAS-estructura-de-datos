// Shared display helpers for money and duration across panels.

export function formatMoney(value) {
  const n = Number(value);
  return Number.isFinite(n) ? `$${n.toFixed(2)}` : "-";
}

export function formatMinutes(min) {
  const m = Number(min);
  if (!Number.isFinite(m) || m < 0) return "-";
  return `${Math.floor(m / 60)} h ${Math.round(m % 60)} min`;
}
