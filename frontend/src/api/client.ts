const API_BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  })

  if (!res.ok) {
    let detail = 'Erro na requisição'
    try {
      const body = await res.json()
      detail = body.detail ?? detail
      if (Array.isArray(detail)) {
        detail = detail.map((d: { msg?: string }) => d.msg).join(', ')
      }
    } catch {
      
    }
    throw new ApiError(res.status, String(detail))
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}
