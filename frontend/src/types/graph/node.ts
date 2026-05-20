export interface NodeData {
  id: string
  entity_type: string
  type?: string | null
  label?: string | null
  /** @deprecated Frontend computes GPU layout via cosmos.gl cluster API */
  x?: number | null
  /** @deprecated Frontend computes GPU layout via cosmos.gl cluster API */
  y?: number | null
  /** @deprecated Lives in AnalysisResult.node_scoring.scores; kept for legacy mode */
  risk_score?: number | null
  alerts: string[]
  in_flow: number
  out_flow: number
  is_laundering_node: boolean
  attributes: Record<string, unknown>
}
