import type { DocumentRecord, Evidence, Program, ProgramSetup } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || "Request failed");
  return response.json() as Promise<T>;
}

export const api = {
  documents: () => request<DocumentRecord[]>("/api/documents"),
  scan: () => request<{ id: string }>("/api/documents/scan", { method: "POST" }),
  job: (id: string) => request<{ status: string }>(`/api/jobs/${id}`),
  page: (id: string, page: number) => request<{ text: string }>(`/api/documents/${id}/pages/${page}`),
  setup: () => request<ProgramSetup>("/api/program-setup"),
  saveSetup: (setup: Omit<ProgramSetup, "version">) => request<ProgramSetup>("/api/program-setup", { method: "PUT", body: JSON.stringify(setup) }),
  programs: () => request<Program[]>("/api/programs"),
  createProgram: (payload: Pick<Program, "name_en" | "classification" | "field_values" | "status" | "confidence">) => request<Program>("/api/programs", { method: "POST", body: JSON.stringify(payload) }),
  addEvidence: (programId: string, payload: Evidence) => request<Program>(`/api/programs/${programId}/evidence`, { method: "POST", body: JSON.stringify(payload) }),
  updateProgram: (id: string, payload: Partial<Pick<Program, "name_en" | "classification" | "field_values" | "status" | "confidence">>) => request<Program>(`/api/programs/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
};
