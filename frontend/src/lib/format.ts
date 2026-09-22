

const brl = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

export function formatBRL(cents: number): string {
  return brl.format(cents / 100)
}

export function formatDateBR(iso: string | null | undefined): string {
  if (!iso) return 'Sem data'
  const d = new Date(iso)
  return d.toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' })
}

export function formatDateTimeBR(iso: string | null | undefined): string {
  if (!iso) return 'Sem data'
  const d = new Date(iso)
  return d.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })
}

export function formatSlaCell(
  status: string,
  slaDeadline: string | null | undefined,
): { label: string; tone: 'muted' | 'ok' | 'late' | 'pending' } {
  if (status === 'cotado' || !slaDeadline) {
    return { label: 'Após aceite', tone: 'pending' }
  }
  if (status === 'pago' || status === 'cancelado') {
    return { label: formatDateBR(slaDeadline), tone: 'muted' }
  }
  const deadline = new Date(slaDeadline)
  const late = deadline.getTime() < Date.now()
  if (status === 'aceito' || status === 'em_transito') {
    return {
      label: late ? `Atrasado · ${formatDateBR(slaDeadline)}` : formatDateBR(slaDeadline),
      tone: late ? 'late' : 'ok',
    }
  }
  return { label: formatDateBR(slaDeadline), tone: 'muted' }
}

export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    cotado: 'Cotado',
    aceito: 'Aceito',
    em_transito: 'Em trânsito',
    entregue: 'Entregue',
    pago: 'Pago',
    cancelado: 'Cancelado',
  }
  return map[status] ?? status
}
