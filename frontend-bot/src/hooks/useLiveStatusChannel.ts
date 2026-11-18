import { useEffect, useState } from 'react'

import { ReconnectingSocket, wsUrl, type ConnectionStatus } from '@/lib/reconnectingSocket'
import type { AuthService } from '@/services/auth/AuthService'
import { authService as defaultAuthService } from '@/services/auth/HttpAuthService'

/*
 * Canal /ws/estado: un solo socket que avisa cuándo CUALQUIER usuario
 * empieza o deja de compartir su ubicación en tiempo real.
 *
 *   {"tipo": "estado", "telegram_id", "en_vivo", "en_vivo_hasta", "fecha"}
 *
 * No manda coordenadas ni un estado inicial: al (re)conectar hay que pedir
 * la lista por REST (``onOpen``) para no perder cambios ocurridos mientras
 * estaba desconectado.
 */

export interface LiveStatusChange {
  telegramId: number
  isLive: boolean
  liveUntil: string | null
  changedAt: string
}

interface StatusDto {
  tipo: 'estado'
  telegram_id: number
  en_vivo: boolean
  en_vivo_hasta: string | null
  fecha: string
}

function parseStatus(raw: string): LiveStatusChange | null {
  let data: StatusDto
  try {
    data = JSON.parse(raw)
  } catch {
    return null
  }
  if (data.tipo !== 'estado') return null
  return {
    telegramId: data.telegram_id,
    isLive: data.en_vivo,
    liveUntil: data.en_vivo_hasta,
    changedAt: data.fecha,
  }
}

interface Handlers {
  onChange?: (change: LiveStatusChange) => void
  /** Se abrió o reabrió la conexión. */
  onOpen?: () => void
  /** Error definitivo (p. ej. la sesión ya no se puede renovar). */
  onError?: (error: unknown) => void
}

/** Guarda los callbacks más recientes sin reconectar al cambiarlos. */
class HandlerBox {
  handlers: Handlers = {}
  set(handlers: Handlers): void {
    this.handlers = handlers
  }
}

interface UseLiveStatusChannelOptions extends Handlers {
  /** Por defecto `/ws/estado` en el backend. */
  url?: string
  auth?: AuthService
}

/**
 * Se conecta al montar y se desconecta al desmontar.
 * `url` y `auth` se leen una sola vez; los callbacks pueden cambiar en cada render.
 */
export function useLiveStatusChannel({
  url,
  auth = defaultAuthService,
  ...handlers
}: UseLiveStatusChannelOptions = {}) {
  const [status, setStatus] = useState<ConnectionStatus>('connecting')

  // Los callbacks se leen de aquí en cada evento, así nunca quedan viejos.
  const [current] = useState(() => new HandlerBox())
  useEffect(() => {
    current.set(handlers)
  })

  const [socket] = useState(
    () =>
      new ReconnectingSocket({
        url: url ?? wsUrl('/ws/estado'),
        auth,
        handshake: (token) => ({ token }),
        onMessage: (raw) => {
          const change = parseStatus(raw)
          if (change) current.handlers.onChange?.(change)
        },
        onStatus: setStatus,
        onOpen: () => current.handlers.onOpen?.(),
        onError: (error) => current.handlers.onError?.(error),
      }),
  )

  useEffect(() => {
    const retry = () => socket.retryNow()
    socket.start()
    window.addEventListener('online', retry)
    return () => {
      window.removeEventListener('online', retry)
      socket.stop()
    }
  }, [socket])

  return { status }
}
