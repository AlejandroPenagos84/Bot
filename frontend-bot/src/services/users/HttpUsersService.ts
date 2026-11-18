import { AuthError, type AuthService } from '@/services/auth/AuthService'
import { authService as defaultAuthService } from '@/services/auth/HttpAuthService'
import type { LastLocation, MonitoredUser, UsersService } from './UsersService'

interface UserSummaryDto {
  telegram_id: number
  telefono: string | null
  en_vivo: boolean
  ultima_fecha: string | null
}

interface UbicationDto {
  telegram_id: number
  lat: number
  lon: number
  fecha: string
  en_vivo: boolean
  en_vivo_hasta: string | null
}

/**
 * Implementación contra `/api/v1/usuarios` (FastAPI).
 *
 * Usa el access token de `AuthService`. Si vence (401), lo renueva una vez
 * con la cookie de refresh y reintenta; si eso falla, lanza `AuthError`
 * con status 401 para que la UI cierre la sesión.
 */
export class HttpUsersService implements UsersService {
  private readonly baseUrl: string
  private readonly auth: AuthService

  constructor(auth: AuthService, baseUrl: string = import.meta.env.VITE_API_URL ?? '') {
    this.auth = auth
    this.baseUrl = `${baseUrl.replace(/\/$/, '')}/api/v1/usuarios`
  }

  async listUsers(): Promise<MonitoredUser[]> {
    const response = await this.authorizedFetch('')
    await this.ensureOk(response)
    const dtos = (await response.json()) as UserSummaryDto[]
    return dtos.map((dto) => ({
      telegramId: dto.telegram_id,
      phone: dto.telefono,
      isLive: dto.en_vivo,
      lastSeen: dto.ultima_fecha,
    }))
  }

  async getLastLocation(telegramId: number): Promise<LastLocation | null> {
    const response = await this.authorizedFetch(`/${telegramId}/ubicacion`)
    if (response.status === 404) return null
    await this.ensureOk(response)
    const dto = (await response.json()) as UbicationDto
    return {
      telegramId: dto.telegram_id,
      latitude: dto.lat,
      longitude: dto.lon,
      recordedAt: dto.fecha,
      isLive: dto.en_vivo,
      liveUntil: dto.en_vivo_hasta,
    }
  }

  private async authorizedFetch(path: string): Promise<Response> {
    if (!this.auth.getAccessToken()) await this.auth.refresh()

    let response = await this.send(path)
    if (response.status === 401) {
      await this.auth.refresh() // lanza AuthError si la sesión ya no es válida
      response = await this.send(path)
    }
    return response
  }

  private async send(path: string): Promise<Response> {
    try {
      return await fetch(`${this.baseUrl}${path}`, {
        headers: { Authorization: `Bearer ${this.auth.getAccessToken() ?? ''}` },
        credentials: 'include',
      })
    } catch {
      throw new AuthError('NETWORK_ERROR', 'No se pudo conectar con el servidor', 0)
    }
  }

  private async ensureOk(response: Response): Promise<void> {
    if (response.ok) return
    const body = (await response.json().catch(() => ({}))) as { detail?: string }
    throw new AuthError('HTTP_ERROR', body.detail ?? response.statusText, response.status)
  }
}

/** Instancia por defecto que usa la app. */
export const usersService: UsersService = new HttpUsersService(defaultAuthService)
