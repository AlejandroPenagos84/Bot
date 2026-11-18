import {
  AuthError,
  type AuthService,
  type LoginCredentials,
  type Session,
  type User,
} from './AuthService'

interface TokenResponseDto {
  access_token: string
  token_type: string
  expires_in: number
}

interface UserResponseDto {
  id: string
  username: string
  email: string
  status: string
  role: string
  created_at: string
}

interface ErrorResponseDto {
  error?: { code?: string; message?: string }
}

/**
 * Implementación contra la API FastAPI (`/api/v1/auth`).
 *
 * - El access token se guarda solo en memoria (no en localStorage).
 * - El refresh token lo maneja el navegador como cookie httpOnly, por eso
 *   todas las peticiones van con `credentials: 'include'`.
 */
export class HttpAuthService implements AuthService {
  private readonly baseUrl: string
  private accessToken: string | null = null

  constructor(baseUrl: string = import.meta.env.VITE_API_URL ?? '') {
    this.baseUrl = `${baseUrl.replace(/\/$/, '')}/api/v1/auth`
  }

  async login(credentials: LoginCredentials): Promise<Session> {
    const dto = await this.request<TokenResponseDto>('/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    })
    return this.storeSession(dto)
  }

  async refresh(): Promise<Session> {
    try {
      const dto = await this.request<TokenResponseDto>('/refresh', { method: 'POST' })
      return this.storeSession(dto)
    } catch (error) {
      this.accessToken = null
      throw error
    }
  }

  async logout(): Promise<void> {
    try {
      await this.request<void>('/logout', { method: 'POST' })
    } finally {
      this.accessToken = null
    }
  }

  async me(): Promise<User> {
    const dto = await this.request<UserResponseDto>('/me', { method: 'GET' }, true)
    return {
      id: dto.id,
      username: dto.username,
      email: dto.email,
      status: dto.status,
      role: dto.role,
      createdAt: dto.created_at,
    }
  }

  getAccessToken(): string | null {
    return this.accessToken
  }

  private storeSession(dto: TokenResponseDto): Session {
    this.accessToken = dto.access_token
    return { accessToken: dto.access_token, expiresIn: dto.expires_in }
  }

  private async request<T>(path: string, init: RequestInit, withAuth = false): Promise<T> {
    const headers = new Headers(init.headers)
    if (init.body) headers.set('Content-Type', 'application/json')
    if (withAuth && this.accessToken) {
      headers.set('Authorization', `Bearer ${this.accessToken}`)
    }

    let response: Response
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        headers,
        credentials: 'include',
      })
    } catch {
      throw new AuthError('NETWORK_ERROR', 'No se pudo conectar con el servidor', 0)
    }

    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as ErrorResponseDto
      throw new AuthError(
        body.error?.code ?? 'HTTP_ERROR',
        body.error?.message ?? response.statusText,
        response.status,
      )
    }

    if (response.status === 204) return undefined as T
    return (await response.json()) as T
  }
}

/** Instancia por defecto que usa la app. */
export const authService: AuthService = new HttpAuthService()
