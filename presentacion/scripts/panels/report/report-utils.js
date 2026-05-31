// Map report legs to graph edge list for highlightRoute().

function pick(obj, ...keys) {
  for (const key of keys) {
    if (obj?.[key] != null && obj[key] !== "") return obj[key];
  }
  return null;
}

export function legsToEdgeList(legs = []) {
  if (!Array.isArray(legs)) return [];

  return legs
    .map(leg => ({
      source: pick(leg, "origin_id", "origin"),
      target: pick(leg, "destination_id", "destination", "dest"),
    }))
    .filter(edge => edge.source && edge.target);
}
