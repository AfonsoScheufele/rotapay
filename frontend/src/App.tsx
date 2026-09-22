import type { ReactNode } from 'react'
import { Navigate, Route, Routes, Link } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { LoginPage } from './pages/LoginPage'
import { FreightsPage } from './pages/FreightsPage'
import { FreightDetailPage } from './pages/FreightDetailPage'
import { DashboardPage } from './pages/DashboardPage'

function Shell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  return (
    <div className="app-shell">
      <nav className="topnav">
        <Link to="/" className="brand-link">
          RotaPay
        </Link>
        <div className="nav-right">
          {user && (
            <>
              <span className="nav-user">
                {user.name}
                <span aria-hidden> · </span>
                {user.role}
              </span>
              <Link to="/">Fretes</Link>
              <Link to="/dashboard">Dashboard</Link>
              <button type="button" className="linkish" onClick={() => void logout()}>
                Sair
              </button>
            </>
          )}
        </div>
      </nav>
      <main>{children}</main>
    </div>
  )
}

function Private({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="page">Carregando sessão…</p>
  if (!user) return <Navigate to="/login" replace />
  return <Shell>{children}</Shell>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <Private>
            <FreightsPage />
          </Private>
        }
      />
      <Route
        path="/fretes/:id"
        element={
          <Private>
            <FreightDetailPage />
          </Private>
        }
      />
      <Route
        path="/dashboard"
        element={
          <Private>
            <DashboardPage />
          </Private>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
