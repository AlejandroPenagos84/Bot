/**
 * Contrato de autenticación del frontend.
 *
 * El hook `useAuth` solo depende de esta interfaz, así que se puede cambiar
 * la implementación (HTTP real, mock para pruebas, otro proveedor) sin tocar
 * los componentes.
 */

export type UserRole = string
export type UserStatus = string

export interface User {
  id: string
  username: string
  email: string
  status: UserStatus
  role: UserRole
  createdAt: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface Session {
  accessToken: string
  /** Segundos de vida del access token. */
  expiresIn: number
}

/** Error normalizado con el formato `{ error: { code, message } }` del backend. */
export class AuthError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = 'AuthError'
    this.code = code
    this.status = status
  }
}

export interface AuthService {
  /** Inicia sesión; el refresh token queda en una cookie httpOnly. */
  login(credentials: LoginCredentials): Promise<Session>
  /** Cierra la sesión en el servidor y descarta el access token. */
  logout(): Promise<void>
  /** Renueva el access token usando la cookie de refresh. */
  refresh(): Promise<Session>
  /** Devuelve el usuario autenticado. */
  me(): Promise<User>
  /** Access token actual en memoria (o `null` si no hay sesión). */
  getAccessToken(): string | null
}
