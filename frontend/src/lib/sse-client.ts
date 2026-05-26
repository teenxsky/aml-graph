import type { GraphMeta } from '@/types/graph/meta'
import type { NodeData } from '@/types/graph/node'
import type { EdgeData } from '@/types/graph/edge'
import type { DetectorResult } from '@/types/graph/detector'
import type { AnalysisMetadata, ClusteringResult } from '@/types/graph/analysis'
import type { SSEHandlers } from '@/types/graph/stream'

export interface SSEClient {
  close: () => void
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? ''

export function createSSEClient(sessionId: string, handlers: SSEHandlers): SSEClient {
  const url = `${API_BASE}/api/v1/graph/${sessionId}/stream`
  const es = new EventSource(url)

  es.addEventListener('graph_meta', e => {
    try {
      handlers.onGraphMeta?.(JSON.parse((e as MessageEvent).data) as GraphMeta)
    } catch {}
  })

  es.addEventListener('nodes_chunk', e => {
    try {
      const data = JSON.parse((e as MessageEvent).data) as { nodes: NodeData[] }
      handlers.onNodesChunk?.(data.nodes)
    } catch {}
  })

  es.addEventListener('edges_chunk', e => {
    try {
      const data = JSON.parse((e as MessageEvent).data) as { edges: EdgeData[] }
      handlers.onEdgesChunk?.(data.edges)
    } catch {}
  })

  es.addEventListener('analysis_result', e => {
    try {
      const raw = JSON.parse((e as MessageEvent).data) as {
        labels: number[]
        node_ids: string[]
        cluster_centroids_2d: [number, number][]
        type_centroids: Record<string, [number, number]>
        n_clusters: number
        method: string
        metadata: AnalysisMetadata
      }
      const clustering: ClusteringResult = {
        method: raw.method as ClusteringResult['method'],
        labels: raw.labels,
        node_ids: raw.node_ids,
        n_clusters: raw.n_clusters,
        cluster_centroids_2d: raw.cluster_centroids_2d ?? null,
        type_centroids: raw.type_centroids ?? {},
        metadata: raw.metadata
      }
      handlers.onAnalysisResult?.({ clustering, node_scoring: null })
    } catch {}
  })

  es.addEventListener('completed', e => {
    try {
      const data = JSON.parse((e as MessageEvent).data) as { job_id: string }
      handlers.onCompleted?.(data)
    } catch {}
  })

  es.addEventListener('status', e => {
    try {
      const data = JSON.parse((e as MessageEvent).data) as { status: string; job_id: string }
      handlers.onStatus?.(data)
    } catch {}
  })

  es.addEventListener('error', e => {
    try {
      const data = JSON.parse((e as MessageEvent).data) as { message: string }
      handlers.onServerError?.(data)
    } catch {}
  })

  es.addEventListener('detector_result', e => {
    try {
      handlers.onDetectorResult?.(JSON.parse((e as MessageEvent).data) as DetectorResult)
    } catch {}
  })

  es.addEventListener('stream_done', () => {
    handlers.onStreamDone?.()
    es.close()
  })

  es.onerror = e => {
    handlers.onError?.(e)
  }

  return { close: () => es.close() }
}
