import { API } from "../config";
import { buildHeaders, handleResponse } from "./helper";

export async function login(email, password) {
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({ email, password }),
  });

  return handleResponse(res);
}