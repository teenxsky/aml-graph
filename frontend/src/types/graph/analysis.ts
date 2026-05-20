/**
 * Track A: cluster labels from AGC or Louvain.
 * labels[i] corresponds to nodes[i] in the stream.
 */
export interface ClusteringResult {
  method: 'agc' | 'louvain'
  labels: number[] // (n,) int — index aligned to node_ids
  /** Идентификаторы узлов в том же порядке что и labels */
  node_ids: string[]
  n_clusters: number
  cluster_centroids_2d: [number, number][] | null // seed positions for cosmos.gl
  metadata: Record<string, unknown>
}

/**
 * Track B: per-node risk scores from GNN or heuristic passthrough.
 * scores[i] corresponds to nodes[i] in the stream.
 * Consumed INDEPENDENTLY from ClusteringResult.
 */
export interface NodeScoringResult {
  method: string
  scores: number[] // (n,) ∈ [0, 1] — index aligned to streamed nodes
  metadata: Record<string, unknown>
}

export interface AnalysisResult {
  clustering: ClusteringResult | null
  node_scoring: NodeScoringResult | null
}

export type ClusteringMethod = 'agc' | 'louvain' | 'none'
export type ScoringMethod = 'heuristic' | 'gnn' | 'none'
