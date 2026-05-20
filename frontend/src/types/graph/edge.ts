export interface EdgeData {
  id?: string | null
  source: string
  target: string
  amount_paid: number
  timestamp: number
  risk_score: number
  alerts: string[]
  amount_received?: number | null
  payment_currency?: string | null
  receiving_currency?: string | null
  payment_format?: string | null
  is_laundering?: boolean | null
  attributes: Record<string, unknown>
}
