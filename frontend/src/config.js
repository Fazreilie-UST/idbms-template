export const API =
  window._env_?.API ||
  (typeof process !== "undefined" && process.env.API) ||
  "http://localhost:8000/api/v1";