export async function handleResponse(res) {
  if (!res.ok) {
    let message = "Request failed";

    try {
      const err = await res.json();
      message = err.detail || err.message || message;
    } catch {
      message = res.statusText || message;
    }

    throw new Error(message);
  }

  return res.json();
}

export function buildHeaders(token = null) {
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}