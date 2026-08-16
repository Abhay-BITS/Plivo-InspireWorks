import { ApiError, connectLiveSocket, listCalls, placeCall } from "./api";
import type { LiveEvent } from "./api";
import { CallList } from "./call-list";
import { StateGraph } from "./state-graph";
import { Timeline } from "./timeline";
import { XmlInspector } from "./xml-inspector";

const statusDot = document.getElementById("status-dot") as HTMLElement;
const statusLabel = document.getElementById("status-label") as HTMLElement;
const form = document.getElementById("place-call-form") as HTMLFormElement;
const toInput = document.getElementById("to-input") as HTMLInputElement;
const fromValue = document.getElementById("from-value") as HTMLElement;
const formMessage = document.getElementById("form-message") as HTMLElement;
const callListEl = document.getElementById("call-list") as HTMLUListElement;
const stateGraphEl = document.getElementById("state-graph") as HTMLElement;
const timelineEl = document.getElementById("timeline") as HTMLUListElement;
const xmlTitleEl = document.getElementById("xml-title") as HTMLElement;
const xmlInspectorEl = document.getElementById("xml-inspector") as HTMLElement;
const demoCodeRow = document.getElementById("demo-code-row") as HTMLElement;
const demoCodeEl = document.getElementById("demo-code") as HTMLElement;

let selectedCallUuid: string | null = null;
const lastDigitsByCall = new Map<string, string>();
const knownCallStates = new Map<string, string>();

const stateGraph = new StateGraph(stateGraphEl);
const timeline = new Timeline(timelineEl);
const xmlInspector = new XmlInspector(xmlTitleEl, xmlInspectorEl);

const callList = new CallList(callListEl, (callUuid) => {
  selectedCallUuid = callUuid;
  const state = knownCallStates.get(callUuid) ?? "AWAITING_OTP";
  stateGraph.render(callUuid, state);
  timeline.render(callUuid);
  xmlInspector.render(callUuid);
});

function setConnectionStatus(connected: boolean): void {
  statusDot.classList.toggle("connected", connected);
  statusDot.classList.toggle("disconnected", !connected);
  statusLabel.textContent = connected ? "connected" : "disconnected";
}

async function refreshCallList(): Promise<void> {
  try {
    const calls = await listCalls();
    for (const call of calls) knownCallStates.set(call.call_uuid, call.state);
    callList.setCalls(calls);
  } catch {
    // The list will pick itself up on the next successful poll.
  }
}

function handleLiveEvent(event: LiveEvent): void {
  timeline.record(event);
  if (event.type === "xml_served") {
    xmlInspector.record(event);
  }
  if (event.type === "dtmf") {
    lastDigitsByCall.set(event.call_uuid, event.digits);
  }
  if (event.type === "state_change") {
    knownCallStates.set(event.call_uuid, event.to);
    const digits = lastDigitsByCall.get(event.call_uuid);
    stateGraph.applyTransition(event.call_uuid, event.from, event.to, digits);
  }
  if (event.type === "call_ended") {
    knownCallStates.set(event.call_uuid, event.final_state);
  }

  if (!selectedCallUuid) {
    selectedCallUuid = event.call_uuid;
  }
  if (event.call_uuid === selectedCallUuid) {
    timeline.render(selectedCallUuid);
    if (event.type === "xml_served") xmlInspector.render(selectedCallUuid);
    if (event.type === "state_change") stateGraph.render(selectedCallUuid, event.to);
  }

  if (event.type === "state_change" || event.type === "call_ended") {
    void refreshCallList();
  }
}

function connect(): void {
  connectLiveSocket({
    onOpen: () => setConnectionStatus(true),
    onClose: () => {
      setConnectionStatus(false);
      setTimeout(connect, 2000);
    },
    onEvent: handleLiveEvent,
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = form.querySelector("button") as HTMLButtonElement;
  formMessage.textContent = "";
  formMessage.classList.remove("error");
  submitButton.disabled = true;

  try {
    await placeCall(toInput.value.trim());
    formMessage.textContent = "Call placed.";
    void refreshCallList();
  } catch (error) {
    formMessage.classList.add("error");
    formMessage.textContent = error instanceof ApiError ? error.message : "Something went wrong.";
  } finally {
    submitButton.disabled = false;
  }
});

async function loadConfig(): Promise<void> {
  const resp = await fetch("/api/config");
  if (!resp.ok) return;
  const config = await resp.json();
  fromValue.textContent = config.from_number;
  toInput.value = config.default_destination ?? "";
  if (config.demo_otp_code) {
    demoCodeRow.hidden = false;
    demoCodeEl.textContent = config.demo_otp_code;
  }
}

void loadConfig();
void refreshCallList();
setInterval(() => void refreshCallList(), 5000);
connect();
