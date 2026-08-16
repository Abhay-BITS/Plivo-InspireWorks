import type { CallSummary } from "./api";

function maskNumber(number: string): string {
  if (number.length <= 4) return number;
  return `...${number.slice(-4)}`;
}

function formatDuration(createdAt: string): string {
  const elapsedMs = Date.now() - new Date(createdAt).getTime();
  const totalSeconds = Math.max(0, Math.floor(elapsedMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export class CallList {
  private readonly root: HTMLUListElement;
  private calls: CallSummary[] = [];
  private selected: string | null = null;
  private readonly onSelect: (callUuid: string) => void;

  constructor(root: HTMLUListElement, onSelect: (callUuid: string) => void) {
    this.root = root;
    this.onSelect = onSelect;
  }

  setCalls(calls: CallSummary[]): void {
    this.calls = calls;
    if (!this.selected && calls.length > 0) {
      this.selected = calls[0].call_uuid;
      this.onSelect(this.selected);
    }
    this.render();
  }

  upsert(call: CallSummary): void {
    const index = this.calls.findIndex((c) => c.call_uuid === call.call_uuid);
    if (index >= 0) {
      this.calls[index] = call;
    } else {
      this.calls.unshift(call);
      if (!this.selected) {
        this.selected = call.call_uuid;
        this.onSelect(this.selected);
      }
    }
    this.render();
  }

  select(callUuid: string): void {
    this.selected = callUuid;
    this.onSelect(callUuid);
    this.render();
  }

  private render(): void {
    if (this.calls.length === 0) {
      this.root.innerHTML = '<li class="call-list-empty">No calls yet.</li>';
      return;
    }

    this.root.innerHTML = this.calls
      .map((call) => {
        const isSelected = call.call_uuid === this.selected;
        return `
          <li class="call-row ${isSelected ? "selected" : ""}" data-call-uuid="${call.call_uuid}">
            <span class="call-dot"></span>
            <span class="call-number mono">${maskNumber(call.to_number)}</span>
            <span class="call-duration">${formatDuration(call.created_at)}</span>
          </li>`;
      })
      .join("");

    this.root.querySelectorAll<HTMLLIElement>("[data-call-uuid]").forEach((row) => {
      row.addEventListener("click", () => {
        const uuid = row.dataset.callUuid;
        if (uuid) this.select(uuid);
      });
    });
  }
}
