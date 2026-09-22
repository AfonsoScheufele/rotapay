import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { DashboardSummary } from '../api/types'
import { formatBRL, formatSlaCell, statusLabel } from '../lib/format'

const STATUS_ORDER = [
  'cotado',
  'aceito',
  'em_transito',
  'entregue',
  'pago',
  'cancelado',
] as const

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    void (async () => {
      try {
        const summary = await api<DashboardSummary>('/api/dashboard/summary')
        setData(summary)
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Erro no dashboard')
      }
    })()
  }, [])

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Operação e receita dos fretes pagos</p>
        </div>
      </header>

      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <div className="stats">
            <article className="stat">
              <span className="stat-label">Fretes ativos</span>
              <strong className="stat-value">{data.fretes_ativos}</strong>
            </article>
            <article className="stat">
              <span className="stat-label">Aguardando aceite</span>
              <strong className="stat-value">{data.fretes_aguardando_sla}</strong>
            </article>
            <article className="stat">
              <span className="stat-label">No prazo</span>
              <strong className="stat-value">{data.fretes_sla_no_prazo}</strong>
            </article>
            <article className="stat">
              <span className="stat-label">SLA atrasado</span>
              <strong className={`stat-value${data.fretes_sla_atrasado > 0 ? ' warn' : ''}`}>
                {data.fretes_sla_atrasado}
              </strong>
            </article>
            <article className="stat">
              <span className="stat-label">Receita bruta</span>
              <strong className="stat-value">{formatBRL(data.receita_bruta_cents)}</strong>
            </article>
            <article className="stat">
              <span className="stat-label">Taxas</span>
              <strong className="stat-value">{formatBRL(data.taxas_cents)}</strong>
            </article>
            <article className="stat">
              <span className="stat-label">Líquido motoristas</span>
              <strong className="stat-value">{formatBRL(data.receita_liquida_cents)}</strong>
            </article>
          </div>

          <section className="panel">
            <h2>Por status</h2>
            <div className="status-bars">
              {STATUS_ORDER.map((key) => {
                const count = data.por_status[key] ?? 0
                const total = Object.values(data.por_status).reduce((a, b) => a + b, 0) || 1
                const pct = Math.round((count / total) * 100)
                return (
                  <div key={key} className="status-bar-row">
                    <span className={`badge status-${key}`}>{statusLabel(key)}</span>
                    <div className="status-bar-track" aria-hidden>
                      <div
                        className={`status-bar-fill status-fill-${key}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="status-bar-count">{count}</span>
                  </div>
                )
              })}
            </div>
          </section>

          <section className="panel">
            <div className="panel-head">
              <h2>Fretes recentes</h2>
              <Link to="/">Ver todos</Link>
            </div>
            {data.recentes.length === 0 ? (
              <p className="muted">Nenhum frete no seu escopo ainda.</p>
            ) : (
              <div className="table-wrap nested">
                <table>
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Rota</th>
                      <th>Valor</th>
                      <th>Prazo (SLA)</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recentes.map((f) => {
                      const sla = formatSlaCell(f.status, f.sla_deadline)
                      return (
                        <tr key={f.id}>
                          <td>
                            <span className={`badge status-${f.status}`}>
                              {statusLabel(f.status)}
                            </span>
                          </td>
                          <td>
                            <div className="route">
                              <span>{f.origin_cep}</span>
                              <span aria-hidden>→</span>
                              <span>{f.dest_cep}</span>
                            </div>
                          </td>
                          <td>{formatBRL(f.amount_cents)}</td>
                          <td>
                            <span className={`sla-cell sla-${sla.tone}`}>{sla.label}</span>
                          </td>
                          <td>
                            <Link to={`/fretes/${f.id}`}>Abrir</Link>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
