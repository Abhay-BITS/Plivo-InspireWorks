export interface CallSummary {
  call_uuid: string;
  to_number: string;
  state: string;
  locale: string | null;
  otp_attempts: number;
  is_authenticated: boolean;
  created_at: string;
  ended_at: string | null;
}

export interface BaseEvent {
  type: string;
  call_uuid: string;
  at: string;
}

export interface StateChangeEvent extends BaseEvent {
  type: "state_change";
  from: string;
  to: string;
  reason: string;
}

export interface DtmfEvent extends BaseEvent {
  type: "dtmf";
  digits: string;
  level: string;
  accepted: boolean;
}

export interface XmlServedEvent extends BaseEvent {
  type: "xml_served";
  endpoint: string;
  xml: string;
  duration_ms: number;
}

export interface CallEndedEvent extends BaseEvent {
  type: "call_ended";
  final_state: string;
  duration_seconds: number;
  hangup_cause: string;
}

export type LiveEvent = StateChangeEvent | DtmfEvent | XmlServedEvent | CallEndedEvent;

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function placeCall(to: string): Promise<{ request_uuid: string; to: string }> {
  const resp = await fetch("/api/calls", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ to }),
  });
  const body = await resp.json();
  if (!resp.ok) {
    throw new ApiError(body.detail ?? "Could not place the call.");
  }
  return body;
}

export async function listCalls(): Promise<CallSummary[]> {
  const resp = await fetch("/api/calls");
  if (!resp.ok) {
    throw new ApiError("Could not load active calls.");
  }
  return resp.json();
}

export interface LiveSocketHandlers {
  onEvent: (event: LiveEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

export function connectLiveSocket(handlers: LiveSocketHandlers): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/live`);

  socket.addEventListener("open", () => handlers.onOpen?.());
  socket.addEventListener("close", () => handlers.onClose?.());
  socket.addEventListener("message", (message) => {
    const data = JSON.parse(message.data as string) as LiveEvent;
    handlers.onEvent(data);
  });

  return socket;
}
