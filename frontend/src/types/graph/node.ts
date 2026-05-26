export interface NodeData {
  id: string
  /** Онтологическая категория: account | individual | business | payment_institution */
  entity_type: string
  /** Поведенческая роль в графе: regular | hub | transit | isolated */
  behavioral_role: string
  type?: string | null
  label?: string | null
  x?: number | null
  y?: number | null
  risk_score?: number | null
  alerts: string[]
  in_flow: number
  out_flow: number
  is_laundering_node: boolean
  attributes: Record<string, unknown>
}
