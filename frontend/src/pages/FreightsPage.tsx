import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { Freight } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { formatBRL, formatSlaCell, statusLabel } from '../lib/format'

export function FreightsPage() {
  const { user } = useAuth()
  const [items, setItems] = useState<Freight[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const [originCep, setOriginCep] = useState('01310-100')
  const [destCep, setDestCep] = useState('80010-000')
  const [weightKg, setWeightKg] = useState('850')
  const [amountReais, setAmountReais] = useState('2500,00')
  const [creating, setCreating] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const data = await api<Freight[]>('/api/freights')
      setItems(data)
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao listar')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      const normalized = amountReais.replace(/\./g, '').replace(',', '.')
      const amount_cents = Math.round(parseFloat(normalized) * 100)
      const weight_grams = Math.round(parseFloat(weightKg.replace(',', '.')) * 1000)
      await api<Freight>('/api/freights', {
        method: 'POST',
        body: JSON.stringify({
          origin_cep: originCep,
          dest_cep: destCep,
          weight_grams,
          amount_cents,
        }),
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao criar frete')
    } finally {
      setCreating(false)
    }
  }

  const canCreate = user?.role === 'embarcador' || user?.role === 'admin'

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Fretes</h1>
          <p className="muted">Coleta e entrega via CEP. Valores em R$.</p>
        </div>
      </header>

      {canCreate && (
        <form className="panel form-grid" onSubmit={onCreate}>
          <h2>Novo frete</h2>
          <label>
            CEP origem
            <input value={originCep} onChange={(e) => setOriginCep(e.target.value)} required />
          </label>
          <label>
            CEP destino
            <input value={destCep} onChange={(e) => setDestCep(e.target.value)} required />
          </label>
          <label>
            Peso (kg)
            <input value={weightKg} onChange={(e) => setWeightKg(e.target.value)} required />
          </label>
          <label>
            Valor (R$)
            <input value={amountReais} onChange={(e) => setAmountReais(e.target.value)} required />
          </label>
          <button type="submit" disabled={creating}>
            {creating ? 'Criando…' : 'Criar frete'}
          </button>
        </form>
      )}

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Carregando…</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Rota</th>
                <th>Valor</th>
                <th title="Prazo máximo de entrega. Definido quando o motorista aceita o frete.">
                  Prazo (SLA)
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((f) => {
                const sla = formatSlaCell(f.status, f.sla_deadline)
                return (
                <tr key={f.id}>
                  <td>
                    <span className={`badge status-${f.status}`}>{statusLabel(f.status)}</span>
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
              {items.length === 0 && (
                <tr>
                  <td colSpan={5}>Nenhum frete ainda.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
