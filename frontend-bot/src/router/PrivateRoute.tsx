import { Navigate, Outlet, useLocation } from 'react-router'

import { useAuth } from '@/hooks/useAuth'

interface PrivateRouteProps {
  children?: React.ReactNode
  /** Ruta a la que se redirige si no hay sesión. */
  redirectTo?: string
}

/**
 * Protege rutas que requieren sesión.
 *
 * Se puede usar envolviendo un elemento (`<PrivateRoute><Page /></PrivateRoute>`)
 * o como ruta layout (`<Route element={<PrivateRoute />}>...</Route>`).
 */
export default function PrivateRoute({ children, redirectTo = '/login' }: PrivateRouteProps) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <div className="flex min-h-svh items-center justify-center text-sm text-muted-foreground">
        Cargando…
      </div>
    )
  }

  if (status === 'unauthenticated') {
    // Guarda la ruta original para volver a ella después del login.
    return <Navigate to={redirectTo} replace state={{ from: location }} />
  }

  return children ? <>{children}</> : <Outlet />
}
