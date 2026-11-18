import { useEffect, useState } from 'react'

import { ReconnectingSocket, wsUrl, type ConnectionStatus } from '@/lib/reconnectingSocket'
import type { AuthService } from '@/services/auth/AuthService'
import { authService as defaultAuthService } from '@/services/auth/HttpAuthService'
import type { LastLocation } from '@/services/users/UsersService'

export type { ConnectionStatus } from '@/lib/reconnectingSocket'

/*
 * Seguimiento en vivo de la ubicación de usuarios por /ws.
 *
 * Una conexión sigue a UN usuario (handshake {"token", "telegram_id"}), así
 * que hay un socket por suscripción. Recibe la última ubicación conocida y
 * luego cada evento:  {"tipo": "ubicacion", ...} | {"tipo": "fin_en_vivo", ...}
 */

export type LiveEvent =
  | { type: 'location'; location: LastLocation }
  | { type: 'ended'; telegramId: number; endedAt: string }

type EventCallback = (event: LiveEvent) => void
type ErrorCallback = (error: unknown, telegramId: number) => void
type StatusCallback = (telegramId: number, status: ConnectionStatus | null) => void

interface LocationDto {
  tipo: 'ubicacion'
  telegram_id: number
  lat: number
  lon: number
  fecha: string
  en_vivo?: boolean
  en_vivo_hasta?: string | null
}

interface EndedDto {
  tipo: 'fin_en_vivo'
  telegram_id: number
  fecha: string
}

function parseEvent(raw: string): LiveEvent | null {
  let data: LocationDto | EndedDto
  try {
    data = JSON.parse(raw)
  } catch {
    return null
  }
  if (data.tipo === 'fin_en_vivo') {
    return { type: 'ended', telegramId: data.telegram_id, endedAt: data.fecha }
  }
  if (data.tipo === 'ubicacion') {
    return {
      type: 'location',
      location: {
        telegramId: data.telegram_id,
        latitude: data.lat,
        longitude: data.lon,
        recordedAt: data.fecha,
        isLive: data.en_vivo ?? false,
        liveUntil: data.en_vivo_hasta ?? null,
      },
    }
  }
  return null
}

interface Subscription {
  socket: ReconnectingSocket
  callback: EventCallback
}

/** Un ``ReconnectingSocket`` por usuario seguido. Sin React. */
class LocationSocketManager {
  private readonly subscriptions = new Map<number, Subscription>()
  private readonly url: string
  private readonly auth: AuthService
  private readonly onStatus: StatusCallback
  private onError: ErrorCallback | undefined

  constructor(url: string, auth: AuthService, onStatus: StatusCallback) {
    this.url = url
    this.auth = auth
    this.onStatus = onStatus
  }

  /** El componente puede pasar un callback nuevo en cada render. */
  setOnError = (onError: ErrorCallback | undefined): void => {
    this.onError = onError
  }

  subscribe = (telegramId: number, callback: EventCallback): void => {
    const existing = this.subscriptions.get(telegramId)
    if (existing) {
      existing.callback = callback
      return
    }
    const subscription: Subscription = {
      callback,
      socket: new ReconnectingSocket({
        url: this.url,
        auth: this.auth,
        handshake: (token) => ({ token, telegram_id: telegramId }),
        onMessage: (raw) => {
          const event = parseEvent(raw)
          if (event) subscription.callback(event)
        },
        onStatus: (status) => this.onStatus(telegramId, status),
        onError: (error) => this.onError?.(error, telegramId),
      }),
    }
    this.subscriptions.set(telegramId, subscription)
    subscription.socket.start()
  }

  unsubscribe = (telegramId: number): void => {
    const subscription = this.subscriptions.get(telegramId)
    if (!subscription) return
    this.subscriptions.delete(telegramId)
    subscription.socket.stop()
    this.onStatus(telegramId, null)
  }

  /**
   * Deja suscritos exactamente estos usuarios: cierra los que sobran y abre
   * los nuevos. Los que ya estaban siguen con su conexión (solo se actualiza
   * el callback).
   */
  sync = (telegramIds: readonly number[], callback: EventCallback): void => {
    const wanted = new Set(telegramIds)
    for (const telegramId of [...this.subscriptions.keys()]) {
      if (!wanted.has(telegramId)) this.unsubscribe(telegramId)
    }
    for (const telegramId of wanted) this.subscribe(telegramId, callback)
  }

  disconnect = (): void => {
    for (const telegramId of [...this.subscriptions.keys()]) this.unsubscribe(telegramId)
  }

  retryNow = (): void => {
    for (const { socket } of this.subscriptions.values()) socket.retryNow()
  }
}

interface UseWebSocketOptions {
  /** URL del WebSocket. Por defecto `/ws` en el backend. */
  url?: string
  /** De aquí sale el access token del handshake y su renovación. */
  auth?: AuthService
  /** Error definitivo de una suscripción (ya no se reintentará). */
  onError?: ErrorCallback
}

/**
 * Uso típico en un componente:
 *   // un usuario
 *   useEffect(() => {
 *     subscribe(id, handleEvent)
 *     return () => unsubscribe(id)
 *   }, [id])
 *
 *   // varios: abre/cierra solo los que cambiaron
 *   useEffect(() => {
 *     sync(ids, handleEvent)
 *   }, [ids])
 *
 * `url` y `auth` se leen una sola vez, al montar.
 */
export function useWebSocketService({
  url,
  auth = defaultAuthService,
  onError,
}: UseWebSocketOptions = {}) {
  const [statuses, setStatuses] = useState<Record<number, ConnectionStatus>>({})

  const [manager] = useState(
    () =>
      new LocationSocketManager(url ?? wsUrl('/ws'), auth, (telegramId, status) =>
        setStatuses((prev) => {
          const next = { ...prev }
          if (status === null) delete next[telegramId]
          else next[telegramId] = status
          return next
        }),
      ),
  )

  // Siempre la versión más reciente del callback, sin reconectar al cambiarlo.
  useEffect(() => {
    manager.setOnError(onError)
  })

  useEffect(() => {
    window.addEventListener('online', manager.retryNow)
    return () => {
      window.removeEventListener('online', manager.retryNow)
      manager.disconnect()
    }
  }, [manager])

  return {
    subscribe: manager.subscribe,
    unsubscribe: manager.unsubscribe,
    sync: manager.sync,
    disconnect: manager.disconnect,
    /** Estado de conexión por `telegramId` (solo de los suscritos). */
    statuses,
  }
}
