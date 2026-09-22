export type UserRole = 'admin' | 'embarcador' | 'motorista'

export type FreightStatus =
  | 'cotado'
  | 'aceito'
  | 'em_transito'
  | 'entregue'
  | 'pago'
  | 'cancelado'

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  document_masked: string
  created_at: string
}

export interface Payment {
  id: string
  freight_id: string
  status: string
  amount_cents: number
  mp_payment_id: string | null
  qr_code: string | null
  qr_code_base64: string | null
  copy_paste: string | null
  driver_payout_recorded_cents: number | null
  paid_at: string | null
  created_at: string
}

export interface Freight {
  id: string
  shipper_id: string
  driver_id: string | null
  status: FreightStatus
  origin_cep: string
  origin_address: string
  origin_lat: number
  origin_lng: number
  dest_cep: string
  dest_address: string
  dest_lat: number
  dest_lng: number
  weight_grams: number
  amount_cents: number
  platform_fee_cents: number
  driver_net_cents: number
  sla_deadline: string | null
  created_at: string
  updated_at: string
  shipper?: User | null
  driver?: User | null
  latest_payment?: Payment | null
  distance_km?: number | null
}

export interface DashboardSummary {
  fretes_ativos: number
  fretes_sla_atrasado: number
  fretes_sla_no_prazo: number
  fretes_aguardando_sla: number
  receita_bruta_cents: number
  taxas_cents: number
  receita_liquida_cents: number
  por_status: Record<string, number>
  recentes: Array<{
    id: string
    status: FreightStatus
    origin_cep: string
    dest_cep: string
    amount_cents: number
    sla_deadline: string | null
    sla_state: string
  }>
  sla_min_hours: number
}
