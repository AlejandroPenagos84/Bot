import { MapPinIcon, MapPinOffIcon, XIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { LiveBadge } from "@/components/molecules/LiveBadge"
import type { ConnectionStatus } from "@/hooks/webSocketHook"
import type { LastLocation } from "@/services/users/UsersService"

interface LocationPanelProps {
  /** Nombre del usuario seleccionado; `null` si no hay ninguno. */
  title: string | null
  location: LastLocation | null
  loading?: boolean
  error?: string | null
  /** Estado del canal en tiempo real; sin valor no se muestra nada. */
  connection?: ConnectionStatus
  /** Si se pasa, muestra un botón para quitar este panel. */
  onClose?: () => void
}

const CONNECTION_TEXT: Record<ConnectionStatus, string | null> = {
  connecting: "Conectando en tiempo real…",
  open: null,
  reconnecting: "Reconectando…",
  failed: "Sin actualizaciones en tiempo real",
}

const dateFormat = new Intl.DateTimeFormat("es-CO", {
  dateStyle: "medium",
  timeStyle: "medium",
})

function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso))
}

function Coordinate({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-muted/60 p-4">
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-mono text-2xl font-semibold tabular-nums">{value.toFixed(6)}</dd>
    </div>
  )
}

function Message({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center text-sm text-muted-foreground">
      {icon}
      <p>{text}</p>
    </div>
  )
}

export function LocationPanel({
  title,
  location,
  loading = false,
  error = null,
  connection,
  onClose,
}: LocationPanelProps) {
  const connectionText = connection ? CONNECTION_TEXT[connection] : null

  if (title === null) {
    return (
      <section className="flex min-h-64 flex-col rounded-xl border bg-card">
        <Message
          icon={<MapPinIcon className="size-8" />}
          text="Selecciona uno o varios usuarios para ver su última ubicación."
        />
      </section>
    )
  }

  return (
    <section className="flex min-h-64 flex-col rounded-xl border bg-card" aria-busy={loading}>
      <header className="flex items-center justify-between gap-2 border-b px-4 py-3">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold">{title}</h2>
          {connectionText && (
            <p role="status" className="truncate text-xs text-muted-foreground">
              {connectionText}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {location && <LiveBadge live={location.isLive} />}
          {onClose && (
            <Button variant="ghost" size="icon-xs" aria-label={`Quitar ${title}`} onClick={onClose}>
              <XIcon />
            </Button>
          )}
        </div>
      </header>

      {loading ? (
        <Message icon={<MapPinIcon className="size-8 animate-pulse" />} text="Cargando ubicación…" />
      ) : error ? (
        <p role="alert" className="p-4 text-sm text-destructive">
          {error}
        </p>
      ) : !location ? (
        <Message
          icon={<MapPinOffIcon className="size-8" />}
          text="Este usuario aún no ha compartido su ubicación."
        />
      ) : (
        <div className="flex flex-col gap-4 p-4">
          <dl className="grid gap-3 sm:grid-cols-2">
            <Coordinate label="Latitud" value={location.latitude} />
            <Coordinate label="Longitud" value={location.longitude} />
          </dl>
          <dl className="grid gap-1 text-sm">
            <div className="flex flex-wrap gap-x-2">
              <dt className="text-muted-foreground">Registrada:</dt>
              <dd>{formatDate(location.recordedAt)}</dd>
            </div>
            {location.isLive && (
              <div className="flex flex-wrap gap-x-2">
                <dt className="text-muted-foreground">En vivo hasta:</dt>
                <dd>{location.liveUntil ? formatDate(location.liveUntil) : "Sin límite"}</dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </section>
  )
}
