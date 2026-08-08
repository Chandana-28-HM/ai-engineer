export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (body?.detail) {
      if (typeof body.detail === "string") return body.detail;
      if (Array.isArray(body.detail)) {
        return (body.detail as { msg: string }[]).map((d) => d.msg).join("; ");
      }
      return JSON.stringify(body.detail);
    }
    return body?.message ?? `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status})`;
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export interface SSEHandler {
  onEvent?: (event: string, data: unknown) => void;
  onDone?: () => void;
  onError?: (message: string) => void;
}

export async function streamSSE(
  path: string,
  payload: unknown,
  handlers: SSEHandler,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    handlers.onError?.("Could not reach the backend. Is it running on port 8001?");
    return;
  }
  if (!res.ok) {
    handlers.onError?.(await parseError(res));
    return;
  }
  if (!res.body) {
    handlers.onError?.("No response stream.");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sepIndex: number;
    while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);
      const event = parseSSEEvent(rawEvent);
      if (event) handlers.onEvent?.(event.event, event.data);
    }
  }
  handlers.onDone?.();
}

interface ParsedSSE {
  event: string;
  data: unknown;
}

function parseSSEEvent(raw: string): ParsedSSE | null {
  let event = "message";
  let data: unknown = "";
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data = line.slice(5).trim();
  }
  if (typeof data === "string" && data.startsWith("{")) {
    try {
      data = JSON.parse(data);
    } catch {
      /* keep raw */
    }
  }
  return { event, data };
}
