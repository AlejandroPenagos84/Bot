import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import type { AuthService, LoginCredentials, User } from '@/services/auth/AuthService'
import { authService as defaultAuthService } from '@/services/auth/HttpAuthService'

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

interface AuthContextValue {
  user: User | null
  status: AuthStatus
  isAuthenticated: boolean
  login: (credentials: LoginCredentials) => Promise<User>
  logout: () => Promise<void>
  getAccessToken: () => string | null
}

const AuthContext = createContext<AuthContextValue | null>(null)

interface AuthProviderProps {
  children: React.ReactNode
  /** Permite inyectar otra implementación (p. ej. un mock en pruebas). */
  service?: AuthService
}

export function AuthProvider({ children, service = defaultAuthService }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  // Al cargar la app intenta restaurar la sesión con la cookie de refresh.
  useEffect(() => {
    let cancelled = false
    service
      .refresh()
      .then(() => service.me())
      .then((current) => {
        if (cancelled) return
        setUser(current)
        setStatus('authenticated')
      })
      .catch(() => {
        if (cancelled) return
        setUser(null)
        setStatus('unauthenticated')
      })
    return () => {
      cancelled = true
    }
  }, [service])

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      await service.login(credentials)
      const current = await service.me()
      setUser(current)
      setStatus('authenticated')
      return current
    },
    [service],
  )

  const logout = useCallback(async () => {
    try {
      await service.logout()
    } finally {
      setUser(null)
      setStatus('unauthenticated')
    }
  }, [service])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      isAuthenticated: status === 'authenticated',
      login,
      logout,
      getAccessToken: () => service.getAccessToken(),
    }),
    [user, status, login, logout, service],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// oxlint-disable-next-line react/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  }
  return context
}
