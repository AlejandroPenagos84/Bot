/**
 * Contrato para consultar los usuarios del bot y sus ubicaciones.
 *
 * Las páginas dependen solo de esta interfaz; la implementación (HTTP, mock,
 * WebSocket...) se puede cambiar sin tocarlas.
 */

export interface MonitoredUser {
  telegramId: number
  phone: string | null
  /** Está compartiendo ubicación en tiempo real ahora mismo. */
  isLive: boolean
  /** Fecha (ISO) de la última ubicación recibida, o `null` si nunca compartió. */
  lastSeen: string | null
}

export interface LastLocation {
  telegramId: number
  latitude: number
  longitude: number
  /** Fecha (ISO) en que se registró la ubicación. */
  recordedAt: string
  isLive: boolean
  /** Hasta cuándo sigue en vivo; `null` si no está en vivo o no tiene límite. */
  liveUntil: string | null
}

export interface UsersService {
  listUsers(): Promise<MonitoredUser[]>
  /** Devuelve `null` si el usuario nunca ha compartido su ubicación. */
  getLastLocation(telegramId: number): Promise<LastLocation | null>
}
