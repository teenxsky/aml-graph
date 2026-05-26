import type { NodeData } from '@/types/graph/node'
import type { EdgeData } from '@/types/graph/edge'
import type { GraphMeta } from '@/types/graph/meta'
import type { DetectorResult } from '@/types/graph/detector'

interface StoreState {
  nodes: Map<string, NodeData>
  edges: EdgeData[]
  detectorResults: DetectorResult[]
  graphMeta: GraphMeta | null
}

const state: StoreState = {
  nodes: new Map(),
  edges: [],
  detectorResults: [],
  graphMeta: null
}

const listeners = new Set<() => void>()

function notify() {
  listeners.forEach(l => l())
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function setGraphMeta(meta: GraphMeta): void {
  state.graphMeta = meta
  notify()
}

export function addNodes(newNodes: NodeData[]): void {
  for (const node of newNodes) {
    state.nodes.set(node.id, node)
  }
  notify()
}

export function addEdges(newEdges: EdgeData[]): void {
  state.edges = state.edges.concat(newEdges)
  notify()
}

export function addDetectorResult(result: DetectorResult): void {
  state.detectorResults = [...state.detectorResults, result]
  notify()
}

export function clearStore(): void {
  state.nodes = new Map()
  state.edges = []
  state.detectorResults = []
  state.graphMeta = null
  notify()
}

export function getSnapshot(): Readonly<StoreState> {
  return {
    nodes: new Map(state.nodes),
    edges: [...state.edges],
    detectorResults: [...state.detectorResults],
    graphMeta: state.graphMeta
  }
}
