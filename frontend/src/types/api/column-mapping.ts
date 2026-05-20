export interface ColumnMapping {
  sender_id: string
  receiver_id: string
  amount_paid: string
  timestamp: string
  device_id?: string | null
  ip_address?: string | null
  sender_bank?: string | null
  receiver_bank?: string | null
  amount_received?: string | null
  payment_currency?: string | null
  receiving_currency?: string | null
  transaction_type?: string | null
  is_laundering?: string | null
}
