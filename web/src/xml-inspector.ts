import type { XmlServedEvent } from "./api";

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function prettyPrintXml(xml: string): string {
  const withBreaks = xml.replace(/></g, ">\n<");
  const lines = withBreaks.split("\n");
  let depth = 0;
  const indented: string[] = [];

  for (const line of lines) {
    const isClosing = /^<\//.test(line);
    const isSelfClosing = /\/>$/.test(line);
    const opensAndCloses = /^<[^/].*>.*<\/.*>$/.test(line);

    if (isClosing) depth = Math.max(0, depth - 1);
    indented.push("  ".repeat(depth) + line);
    if (!isClosing && !isSelfClosing && !opensAndCloses) depth += 1;
  }

  return indented.join("\n");
}

export class XmlInspector {
  private readonly title: HTMLElement;
  private readonly pre: HTMLElement;
  private readonly perCall = new Map<string, XmlServedEvent>();

  constructor(title: HTMLElement, pre: HTMLElement) {
    this.title = title;
    this.pre = pre;
  }

  record(event: XmlServedEvent): void {
    this.perCall.set(event.call_uuid, event);
  }

  render(callUuid: string): void {
    const event = this.perCall.get(callUuid);
    if (!event) {
      this.title.textContent = "XML served";
      this.pre.textContent = "No XML served yet.";
      return;
    }
    this.title.textContent = `XML served  ${event.endpoint}  ${event.duration_ms}ms`;
    this.pre.innerHTML = escapeHtml(prettyPrintXml(event.xml));
  }
}
