import type { LiveEvent } from "./api";

function formatTime(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleTimeString(undefined, { hour12: false });
}

function describe(event: LiveEvent): string {
  switch (event.type) {
    case "state_change":
      return `state &rarr; ${event.to.toLowerCase()}`;
    case "dtmf": {
      const chipClass = event.accepted ? "accepted" : "rejected";
      const chipText = event.accepted ? "accepted" : "rejected";
      return `digits <span class="dtmf-chip ${chipClass} mono">${event.digits}</span> ${chipText}`;
    }
    case "xml_served":
      return `served ${event.endpoint} in ${event.duration_ms}ms`;
    case "call_ended":
      return `call ended, ${event.hangup_cause}`;
  }
}

export class Timeline {
  private readonly list: HTMLUListElement;
  private readonly perCall = new Map<string, LiveEvent[]>();

  constructor(list: HTMLUListElement) {
    this.list = list;
  }

  record(event: LiveEvent): void {
    const events = this.perCall.get(event.call_uuid) ?? [];
    events.push(event);
    if (events.length > 50) {
      events.shift();
    }
    this.perCall.set(event.call_uuid, events);
  }

  render(callUuid: string): void {
    const events = this.perCall.get(callUuid) ?? [];
    if (events.length === 0) {
      this.list.innerHTML = '<li class="timeline-empty">No calls yet. Place one to see the flow.</li>';
      return;
    }

    this.list.innerHTML = events
      .map(
        (event) => `
        <li class="timeline-row">
          <span class="timeline-time">${formatTime(event.at)}</span>
          <span class="timeline-text">${describe(event)}</span>
        </li>`
      )
      .join("");
    this.list.scrollTop = this.list.scrollHeight;
  }
}
