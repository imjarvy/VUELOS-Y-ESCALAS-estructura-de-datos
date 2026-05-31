// Estado y valores iniciales del planner. Sin lógica, sin DOM.
export const state = {
  graphLoaded: false,
  loading: false,
  mode: "basic",        // "basic" | "route"
  itinerary_a: null,
  itinerary_b: null,
  routes: null,
};