/**
 * Hand authored SVG state graph. No graph library: the node coordinates
 * below are the entire layout algorithm, which is what "hand authored"
 * means here.
 */

const CALL_STATES = [
  "AWAITING_OTP",
  "LANGUAGE_MENU",
  "ACTION_MENU",
  "PLAYING_AUDIO",
  "TRANSFERRING",
  "COMPLETED",
] as const;

type NodeId = (typeof CALL_STATES)[number];

const NODE_LABEL: Record<NodeId, string> = {
  AWAITING_OTP: "verify code",
  LANGUAGE_MENU: "language",
  ACTION_MENU: "action menu",
  PLAYING_AUDIO: "audio",
  TRANSFERRING: "transfer",
  COMPLETED: "completed",
};

const NODE_POS: Record<NodeId, { x: number; y: number }> = {
  AWAITING_OTP: { x: 200, y: 36 },
  LANGUAGE_MENU: { x: 200, y: 106 },
  ACTION_MENU: { x: 200, y: 176 },
  PLAYING_AUDIO: { x: 100, y: 250 },
  TRANSFERRING: { x: 300, y: 250 },
  COMPLETED: { x: 200, y: 314 },
};

const NODE_W = 108;
const NODE_H = 34;

interface Edge {
  key: string;
  from: NodeId;
  to: NodeId;
}

const EDGES: Edge[] = [
  { key: "AWAITING_OTP->LANGUAGE_MENU", from: "AWAITING_OTP", to: "LANGUAGE_MENU" },
  { key: "LANGUAGE_MENU->ACTION_MENU", from: "LANGUAGE_MENU", to: "ACTION_MENU" },
  { key: "ACTION_MENU->LANGUAGE_MENU", from: "ACTION_MENU", to: "LANGUAGE_MENU" },
  { key: "ACTION_MENU->PLAYING_AUDIO", from: "ACTION_MENU", to: "PLAYING_AUDIO" },
  { key: "ACTION_MENU->TRANSFERRING", from: "ACTION_MENU", to: "TRANSFERRING" },
  { key: "PLAYING_AUDIO->ACTION_MENU", from: "PLAYING_AUDIO", to: "ACTION_MENU" },
  { key: "TRANSFERRING->ACTION_MENU", from: "TRANSFERRING", to: "ACTION_MENU" },
  { key: "ACTION_MENU->COMPLETED", from: "ACTION_MENU", to: "COMPLETED" },
  { key: "PLAYING_AUDIO->COMPLETED", from: "PLAYING_AUDIO", to: "COMPLETED" },
  { key: "TRANSFERRING->COMPLETED", from: "TRANSFERRING", to: "COMPLETED" },
];

function edgePath(edge: Edge): string {
  const a = NODE_POS[edge.from];
  const b = NODE_POS[edge.to];
  const midX = (a.x + b.x) / 2;
  const midY = (a.y + b.y) / 2;
  if (a.x === b.x) {
    return `M ${a.x} ${a.y + NODE_H / 2} L ${b.x} ${b.y - NODE_H / 2}`;
  }
  return `M ${a.x} ${a.y + NODE_H / 2} Q ${midX} ${midY} ${b.x} ${b.y - NODE_H / 2}`;
}

function edgeMidpoint(edge: Edge): { x: number; y: number } {
  const a = NODE_POS[edge.from];
  const b = NODE_POS[edge.to];
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

export class StateGraph {
  private readonly root: HTMLElement;
  private readonly svg: SVGSVGElement;
  private readonly nodeRects = new Map<NodeId, SVGRectElement>();
  private readonly nodeLabels = new Map<NodeId, SVGTextElement>();
  private readonly edgePaths = new Map<string, SVGPathElement>();
  private readonly visitedStates = new Map<string, Set<NodeId>>();
  private readonly takenEdges = new Map<string, Set<string>>();

  constructor(container: HTMLElement) {
    this.root = container;
    this.svg = this.buildSvg();
    this.root.replaceChildren(this.svg);
  }

  private buildSvg(): SVGSVGElement {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg") as SVGSVGElement;
    svg.setAttribute("viewBox", "0 0 400 340");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Call flow state graph");

    for (const edge of EDGES) {
      const path = document.createElementNS(ns, "path");
      path.setAttribute("d", edgePath(edge));
      path.setAttribute("class", "sg-edge");
      svg.appendChild(path);
      this.edgePaths.set(edge.key, path as SVGPathElement);
    }

    for (const id of CALL_STATES) {
      const pos = NODE_POS[id];
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("x", String(pos.x - NODE_W / 2));
      rect.setAttribute("y", String(pos.y - NODE_H / 2));
      rect.setAttribute("width", String(NODE_W));
      rect.setAttribute("height", String(NODE_H));
      rect.setAttribute("rx", "6");
      rect.setAttribute("class", "sg-node-rect");
      svg.appendChild(rect);
      this.nodeRects.set(id, rect as SVGRectElement);

      const text = document.createElementNS(ns, "text");
      text.setAttribute("x", String(pos.x));
      text.setAttribute("y", String(pos.y + 4));
      text.setAttribute("class", "sg-node-label");
      text.textContent = NODE_LABEL[id];
      svg.appendChild(text);
      this.nodeLabels.set(id, text as SVGTextElement);
    }

    return svg;
  }

  private ensureCall(callUuid: string): void {
    if (!this.visitedStates.has(callUuid)) {
      this.visitedStates.set(callUuid, new Set());
      this.takenEdges.set(callUuid, new Set());
    }
  }

  /** Renders the graph for whichever call is currently selected. */
  render(callUuid: string, currentState: string): void {
    this.ensureCall(callUuid);
    const visited = this.visitedStates.get(callUuid)!;
    const taken = this.takenEdges.get(callUuid)!;

    for (const id of CALL_STATES) {
      const rect = this.nodeRects.get(id)!;
      const label = this.nodeLabels.get(id)!;
      rect.classList.remove("active", "completed");
      label.classList.remove("active");
      if (id === currentState) {
        rect.classList.add("active");
        label.classList.add("active");
      } else if (visited.has(id)) {
        rect.classList.add("completed");
      }
    }

    for (const [key, path] of this.edgePaths) {
      path.classList.toggle("taken", taken.has(key));
    }
  }

  /** Call once per state_change event, with the digit that caused it. */
  applyTransition(callUuid: string, from: string, to: string, digits?: string): void {
    this.ensureCall(callUuid);
    this.visitedStates.get(callUuid)!.add(from as NodeId);
    this.visitedStates.get(callUuid)!.add(to as NodeId);

    const key = `${from}->${to}`;
    const alreadyTaken = this.takenEdges.get(callUuid)!.has(key);
    this.takenEdges.get(callUuid)!.add(key);

    if (!alreadyTaken) {
      const path = this.edgePaths.get(key);
      if (path) {
        this.animateDraw(path);
      }
    }

    if (digits) {
      const edge = EDGES.find((e) => e.key === key);
      if (edge) {
        this.placeDigitPill(edge, digits);
      }
    }

    this.render(callUuid, to);
  }

  /** The only animation in the product: the taken edge draws itself over
   * 400ms. Uses stroke-dasharray/dashoffset rather than a library since a
   * hand authored SVG has no timeline to hook into.
   */
  private animateDraw(path: SVGPathElement): void {
    const length = path.getTotalLength();
    path.style.transition = "none";
    path.style.strokeDasharray = `${length}`;
    path.style.strokeDashoffset = `${length}`;
    path.classList.add("taken");
    path.getBoundingClientRect();
    path.style.transition = "stroke-dashoffset 400ms ease-out";
    path.style.strokeDashoffset = "0";
  }

  private placeDigitPill(edge: Edge, digits: string): void {
    const ns = "http://www.w3.org/2000/svg";
    const { x, y } = edgeMidpoint(edge);

    const pill = document.createElementNS(ns, "rect");
    pill.setAttribute("x", String(x - 14));
    pill.setAttribute("y", String(y - 9));
    pill.setAttribute("width", "28");
    pill.setAttribute("height", "16");
    pill.setAttribute("rx", "8");
    pill.setAttribute("class", "sg-digit-pill");

    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", String(x));
    text.setAttribute("y", String(y + 3));
    text.setAttribute("class", "sg-digit-text");
    text.textContent = digits;

    this.svg.querySelectorAll(`[data-digit-for="${edge.key}"]`).forEach((el) => el.remove());
    pill.setAttribute("data-digit-for", edge.key);
    text.setAttribute("data-digit-for", edge.key);
    this.svg.appendChild(pill);
    this.svg.appendChild(text);
  }
}
