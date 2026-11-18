import type { AuthService } from '@/services/auth/AuthService'

/*
 * Un WebSocket autenticado contra el backend que se reconecta solo.
 *
 * Protocolo común de /ws y /ws/estado (ver src/bot/infrastructure/router.py):
 *   - Al abrir se envía un handshake con el access token.
 *   - Códigos de cierre:
 *       1008  no autorizado        -> renovar token una vez y reintentar
 *       4401  token vencido        -> renovar token y reconectar
 *       otro  (red caída, 1011...) -> reconectar con backoff exponencial
 */

export type ConnectionStatus = 'connecting' | 'open' | 'reconnecting' | 'failed'

const CLOSE_UNAUTHORIZED = 1008
const CLOSE_TOKEN_EXPIRED = 4401

const BASE_DELAY_MS = 1_000
const MAX_DELAY_MS = 30_000
/** Si la conexión duró al menos esto, el siguiente fallo reinicia el backoff. */
const STABLE_AFTER_MS = 10_000

/** URL de un WebSocket del backend: `VITE_WS_URL` + path, o el mismo host. */
export function wsUrl(path: string): string {
  const base = import.meta.env.VITE_WS_URL as string | undefined
  if (base) return `${base.replace(/\/$/, '')}${path}`
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${path}`
}

export interface ReconnectingSocketOptions {
  url: string
  auth: AuthService
  /** Primer mensaje a enviar al abrir. */
  handshake: (token: string) => unknown
  /** Cada mensaje de texto recibido, sin parsear. */
  onMessage: (data: string) => void
  onStatus: (status: ConnectionStatus) => void
  /** Error definitivo: ya no se reintentará. */
  onError: (error: unknown) => void
  /** Se abrió (o reabrió) la conexión. */
  onOpen?: () => void
}

export class ReconnectingSocket {
  private readonly options: ReconnectingSocketOptions
  private socket: WebSocket | null = null
  private timer: number | undefined
  private attempts = 0
  private openedAt = 0
  /** Ya se renovó el token tras un 1008; si vuelve a pasar, se desiste. */
  private authRetried = false
  private active = false

  constructor(options: ReconnectingSocketOptions) {
    this.options = options
  }

  start(): void {
    if (this.active) return
    this.active = true
    this.options.onStatus('connecting')
    void this.open()
  }

  stop(): void {
    this.active = false
    window.clearTimeout(this.timer)
    this.timer = undefined
    const socket = this.socket
    this.socket = null // antes de cerrar, para que ``onclose`` lo ignore
    socket?.close(1000)
  }

  /** Reintenta ya si estaba esperando para reconectar (p. ej. volvió internet). */
  retryNow(): void {
    if (!this.active || this.socket !== null || this.timer === undefined) return
    window.clearTimeout(this.timer)
    this.timer = undefined
    void this.open()
  }

  private async open(): Promise<void> {
    const { auth } = this.options
    let token = auth.getAccessToken()
    if (!token) {
      try {
        token = (await auth.refresh()).accessToken
      } catch (error) {
        this.fail(error)
        return
      }
    }
    if (!this.active) return // se detuvo mientras se renovaba

    const socket = new WebSocket(this.options.url)
    this.socket = socket

    socket.onopen = () => {
      this.openedAt = Date.now()
      socket.send(JSON.stringify(this.options.handshake(token)))
      this.options.onStatus('open')
      this.options.onOpen?.()
    }

    socket.onmessage = (message) => {
      if (typeof message.data !== 'string') return
      this.attempts = 0
      this.authRetried = false
      this.options.onMessage(message.data)
    }

    socket.onclose = (event) => {
      if (this.socket !== socket) return // cierre intencional o socket viejo
      this.socket = null
      void this.handleClose(event.code)
    }
  }

  private async handleClose(code: number): Promise<void> {
    if (Date.now() - this.openedAt >= STABLE_AFTER_MS) {
      this.attempts = 0
      this.authRetried = false
    }

    const mustRefresh =
      code === CLOSE_TOKEN_EXPIRED || (code === CLOSE_UNAUTHORIZED && !this.authRetried)

    if (mustRefresh) {
      if (code === CLOSE_UNAUTHORIZED) this.authRetried = true
      this.options.onStatus('reconnecting')
      try {
        await this.options.auth.refresh()
      } catch (error) {
        this.fail(error) // la sesión ya no se puede renovar
        return
      }
      if (this.active) void this.open()
      return
    }

    if (code === CLOSE_UNAUTHORIZED) {
      this.fail(new Error('El servidor rechazó la conexión'))
      return
    }

    // Caída de red o error del servidor: backoff exponencial con jitter.
    const delay = Math.min(MAX_DELAY_MS, BASE_DELAY_MS * 2 ** this.attempts)
    this.attempts += 1
    this.options.onStatus('reconnecting')
    this.timer = window.setTimeout(() => {
      this.timer = undefined
      void this.open()
    }, delay * (0.5 + Math.random() / 2))
  }

  private fail(error: unknown): void {
    if (!this.active) return
    this.active = false
    this.options.onStatus('failed')
    this.options.onError(error)
  }
}
