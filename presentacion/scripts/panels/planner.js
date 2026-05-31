// Responsibility: API calls for the planner panel.
// The panel handles the DOM; this file handles the fetch.

import { apiPost } from "../api/client.js";

export async function fetchBasicPlan({ origin, budget, time_hours, transport_types, include_secondary }) {
  return await apiPost("/api/plan/basic", {
    origin,
    budget,
    time_hours,
    transport_types,
    include_secondary,
  });
}

export async function fetchBestRoute({ origin, dest, criteria, transport_types, include_secondary }) {
  return await apiPost("/api/plan/route", {
    origin,
    dest,
    criteria,
    transport_types,
    include_secondary,
  });
}