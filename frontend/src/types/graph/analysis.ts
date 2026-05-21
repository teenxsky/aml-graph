export interface StepTiming {
  step: string
  duration_ms: number
  started_at: string // ISO datetime
  finished_at: string
}

export interface AnalysisMetadata {
  n_nodes: number
  n_edges: number
  density: number
  is_directed: boolean

  clustering_method: 'agc' | 'louvain'
  clustering_reason: string
  clustering_extra: Record<string, unknown>

  scoring_weights: {
    detector_alerts: number
    betweenness: number
    pagerank: number
    flow_imbalance: number
  }
  scoring_reason: string
  betweenness_exact: boolean
  betweenness_k: number

  step_timings: StepTiming[]
  total_duration_ms: number

  algorithm_versions: Record<string, string>
}

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
  /** Центры entity-групп в нормализованном пространстве [-1, 1] */
  type_centroids: Record<string, [number, number]>
  metadata: AnalysisMetadata
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

export interface AlgorithmDescription {
  id: string
  name: string
  short_description: string
  detailed_description: string
  reference: string | null
  complexity: string | null
  use_case: string
}
