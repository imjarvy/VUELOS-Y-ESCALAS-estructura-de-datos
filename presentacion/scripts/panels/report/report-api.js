// HTTP calls for the report panel. No DOM, no state.
import { apiGet } from "../../api/client.js";

export async function fetchSessionReport(sessionId) {
  return await apiGet(`/api/report/${sessionId}`);
}
