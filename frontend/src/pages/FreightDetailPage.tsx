import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { Freight, Payment } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { FreightMap } from '../components/FreightMap'
import { formatBRL, formatDateTimeBR, statusLabel } from '../lib/format'

export function FreightDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const [freight, setFreight] = useState<Freight | null>(null)
  const [payment, setPayment] = useState<Payment | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    try {
      const data = await api<Freight>(`/api/freights/${id}`)
      setFreight(data)
      setPayment(data.latest_payment ?? null)
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar')
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  async function runAction(path: string, method = 'POST') {
    if (!id) return
    setBusy(true)
    setError('')
    try {
      const data = await api<Freight | Payment>(path, { method })
      if ('copy_paste' in data) {
        setPayment(data as Payment)
        await load()
      } else {
        setFreight(data as Freight)
        setPayment((data as Freight).latest_payment ?? payment)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Ação falhou')
    } finally {
      setBusy(false)
    }
  }

  async function copyPix() {
    if (!payment?.copy_paste) return
    await navigator.clipboard.writeText(payment.copy_paste)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!freight) {
    return (
      <div className="page">
        {error ? <p className="error">{error}</p> : <p>Carregando…</p>}
        <Link to="/">Voltar</Link>
      </div>
    )
  }

  const isDriver = user?.role === 'motorista'
  const isShipper = user?.role === 'embarcador' || user?.role === 'admin'
  const f = freight

  let wait: string | null = null
  if (f.status !== 'pago' && f.status !== 'cancelado') {
    if (isDriver) {
      if (f.status === 'cotado' && f.driver_id != null) {
        wait = 'Frete já atribuído a outro motorista'
      } else if (f.status === 'entregue') {
        wait = 'Aguardando embarcador gerar Pix'
      }
    } else if (isShipper) {
      if (f.status === 'cotado') wait = 'Aguardando motorista aceitar'
      else if (f.status === 'aceito') wait = 'Aguardando motorista iniciar o trânsito'
      else if (f.status === 'em_transito') wait = 'Aguardando motorista marcar entregue'
    } else if (user?.role === 'admin') {
      if (f.status === 'cotado') wait = 'Aguardando motorista aceitar'
      else if (f.status === 'entregue') wait = 'Aguardando embarcador gerar Pix'
    }
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <Link to="/" className="back">
            Voltar aos fretes
          </Link>
          <h1>Frete {statusLabel(freight.status)}</h1>
          <p className="muted">
            {formatBRL(freight.amount_cents)} · taxa {formatBRL(freight.platform_fee_cents)} ·
            líquido motorista {formatBRL(freight.driver_net_cents)}
          </p>
        </div>
        <span className={`badge status-${freight.status}`}>{statusLabel(freight.status)}</span>
      </header>

      {error && <p className="error">{error}</p>}
      {wait && <p className="next-hint">{wait}</p>}

      <div className="detail-grid">
        <section className="panel">
          <h2>Rota</h2>
          <p>
            <strong>Coleta</strong>
            <br />
            {freight.origin_address}
          </p>
          <p>
            <strong>Entrega</strong>
            <br />
            {freight.dest_address}
          </p>
          <p>
            Peso: {(freight.weight_grams / 1000).toLocaleString('pt-BR')} kg
            {freight.distance_km != null && (
              <>
                <br />
                Distância estimada: {freight.distance_km.toLocaleString('pt-BR')} km
              </>
            )}
          </p>

          <div className="sla-box">
            <strong>Prazo (SLA)</strong>
            {freight.sla_deadline ? (
              <p>
                Até <strong>{formatDateTimeBR(freight.sla_deadline)}</strong>
                {(freight.status === 'aceito' || freight.status === 'em_transito') &&
                  new Date(freight.sla_deadline).getTime() < Date.now() && (
                    <span className="sla-cell sla-late"> (atrasado)</span>
                  )}
              </p>
            ) : (
              <p className="muted">Sem prazo (define no aceite pela distância)</p>
            )}
          </div>
          <div className="actions">
            {isDriver && freight.status === 'cotado' && (
              <button disabled={busy} onClick={() => runAction(`/api/freights/${id}/accept`)}>
                Aceitar frete
              </button>
            )}
            {isDriver && freight.status === 'aceito' && (
              <button disabled={busy} onClick={() => runAction(`/api/freights/${id}/start`)}>
                Iniciar trânsito
              </button>
            )}
            {isDriver && freight.status === 'em_transito' && (
              <button disabled={busy} onClick={() => runAction(`/api/freights/${id}/deliver`)}>
                Marcar entregue
              </button>
            )}
            {isShipper && freight.status === 'entregue' && (
              <button disabled={busy} onClick={() => runAction(`/api/freights/${id}/pix`)}>
                Gerar Pix
              </button>
            )}
            {isShipper && ['cotado', 'aceito', 'em_transito'].includes(freight.status) && (
              <button
                className="danger"
                disabled={busy}
                onClick={() => runAction(`/api/freights/${id}/cancel`)}
              >
                Cancelar
              </button>
            )}
          </div>
        </section>

        <section className="panel">
          <h2>Mapa</h2>
          <FreightMap
            originLat={freight.origin_lat}
            originLng={freight.origin_lng}
            destLat={freight.dest_lat}
            destLng={freight.dest_lng}
            originLabel={freight.origin_address}
            destLabel={freight.dest_address}
          />
        </section>
      </div>

      {payment && (
        <section className="panel pix-panel">
          <h2>Pagamento Pix</h2>
          <p>
            Status: <strong>{payment.status}</strong>
            {payment.paid_at && <> · pago em {formatDateTimeBR(payment.paid_at)}</>}
          </p>
          {payment.qr_code_base64 && (
            <img
              className="qr"
              src={`data:image/png;base64,${payment.qr_code_base64}`}
              alt="QR Code Pix"
            />
          )}
          {payment.copy_paste && (
            <div className="copy-row">
              <code>{payment.copy_paste}</code>
              <button type="button" onClick={() => void copyPix()}>
                {copied ? 'Copiado!' : 'Copia e cola'}
              </button>
            </div>
          )}
          {payment.driver_payout_recorded_cents != null && (
            <p>
              Repasse registrado (líquido):{' '}
              <strong>{formatBRL(payment.driver_payout_recorded_cents)}</strong>
            </p>
          )}
          {payment.status === 'pending' && payment.mp_payment_id?.startsWith('demo-') && (
            <button
              disabled={busy}
              onClick={async () => {
                setBusy(true)
                setError('')
                try {
                  await api('/api/webhooks/mercadopago', {
                    method: 'POST',
                    body: JSON.stringify({
                      type: 'payment',
                      action: 'payment.updated',
                      data: { id: payment.mp_payment_id },
                    }),
                  })
                  await load()
                } catch (err) {
                  setError(err instanceof ApiError ? err.message : 'Webhook falhou')
                } finally {
                  setBusy(false)
                }
              }}
            >
              Simular webhook (demo local)
            </button>
          )}
        </section>
      )}
    </div>
  )
}
