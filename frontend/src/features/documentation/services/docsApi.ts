import { API } from "@/config";
import { apiFetch, authHeaders } from "@/shared/services/helper";

export interface DocTreeNode {
  key: string;
  label: string;
  path?: string;
  embed?: string;
  children?: DocTreeNode[];
}

export interface DocTreeResponse {
  tree: DocTreeNode[];
  can_edit: boolean;
  assets_url_prefix: string;
}

export interface DocPageContent {
  path: string;
  label: string;
  content: string;
  updated_at: string | null;
  embed: string | null;
  can_edit: boolean;
<<<<<<< Updated upstream
=======
  format?: "markdown" | "html";
>>>>>>> Stashed changes
}

export interface DocAsset {
  filename: string;
  url: string;
  size_bytes: number;
  uploaded_at: string;
}

export interface DocAssetList {
  assets: DocAsset[];
}

export async function fetchDocTree(): Promise<DocTreeResponse> {
  return apiFetch<DocTreeResponse>(`${API}/docs/tree`);
}

export async function fetchDocPage(path: string): Promise<DocPageContent> {
  const url = `${API}/docs/page?path=${encodeURIComponent(path)}`;
  return apiFetch<DocPageContent>(url);
}

export async function updateDocPage(
  path: string,
  content: string,
): Promise<DocPageContent> {
  const url = `${API}/docs/page?path=${encodeURIComponent(path)}`;
  return apiFetch<DocPageContent>(url, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export async function fetchDocAssets(): Promise<DocAssetList> {
  return apiFetch<DocAssetList>(`${API}/docs/assets`);
}

export async function uploadDocAsset(file: File): Promise<DocAsset> {
  const form = new FormData();
  form.append("file", file);
  // Don't set Content-Type so the browser supplies the multipart boundary;
  // strip the default JSON header from authHeaders().
  const headers = authHeaders();
  delete headers["Content-Type"];
  const res = await fetch(`${API}/docs/assets`, {
    method: "POST",
    body: form,
    headers,
    credentials: "include",
  });
  if (!res.ok) {
    let detail = "Upload failed";
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await res.json()) as DocAsset;
}

export async function deleteDocAsset(filename: string): Promise<void> {
  const headers = authHeaders();
  delete headers["Content-Type"];
  const res = await fetch(
    `${API}/docs/assets/${encodeURIComponent(filename)}`,
    {
      method: "DELETE",
      headers,
      credentials: "include",
    },
  );
  if (!res.ok && res.status !== 204) {
    let detail = "Delete failed";
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
}
