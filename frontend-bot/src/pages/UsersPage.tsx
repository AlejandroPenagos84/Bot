import { useCallback, useEffect, useRef, useState } from "react"
import { LogOutIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { LocationPanel } from "@/components/organisms/LocationPanel"
import { UserList } from "@/components/organisms/UserList"
import { UsersMap, type MapMarker } from "@/components/organisms/UsersMap"
import { useAuth } from "@/hooks/useAuth"
import { useLiveStatusChannel, type LiveStatusChange } from "@/hooks/useLiveStatusChannel"
import { useWebSocketService, type LiveEvent } from "@/hooks/webSocketHook"
import { userLabel } from "@/lib/users"
import { AuthError } from "@/services/auth/AuthService"
import { usersService as defaultUsersService } from "@/services/users/HttpUsersService"
import type { LastLocation, MonitoredUser, UsersService } from "@/services/users/UsersService"

interface UsersPageProps {
  /** Permite inyectar otra implementación (p. ej. un mock en pruebas). */
  service?: UsersService
}

/** Lo que se muestra de cada usuario seleccionado. */
interface SelectedEntry {
  location: LastLocation | null
  loading: boolean
  error: string | null
}

type Entries = Record<number, SelectedEntry>

function errorMessage(error: unknown): string {
  if (error instanceof AuthError && error.code === "NETWORK_ERROR") return error.message
  return "No se pudo cargar la información. Intenta de nuevo."
}

/** La sesión venció y no se pudo renovar: hay que volver al login. */
function isSessionExpired(error: unknown): boolean {
  return error instanceof AuthError && error.status === 401
}

/**
 * REST y WebSocket pueden responder en cualquier orden: solo se acepta una
 * ubicación si es estrictamente más reciente que la que ya se muestra.
 */
function newest(current: LastLocation | null, incoming: LastLocation | null): LastLocation | null {
  if (!incoming) return current
  if (!current) return incoming
  return Date.parse(incoming.recordedAt) > Date.parse(current.recordedAt) ? incoming : current
}

function endLive(location: LastLocation): LastLocation {
  return { ...location, isLive: false, liveUntil: null }
}

function omit(entries: Entries, telegramId: number): Entries {
  const next = { ...entries }
  delete next[telegramId]
  return next
}

/** Ubicaciones en vivo cuyo ``liveUntil`` ya pasó en ``now``. */
function expiredIds(entries: Entries, now: number): number[] {
  return Object.entries(entries)
    .filter(([, e]) => e.location?.isLive && e.location.liveUntil && Date.parse(e.location.liveUntil) <= now)
    .map(([id]) => Number(id))
}

export default function UsersPage({ service = defaultUsersService }: UsersPageProps) {
  const { user: admin, logout } = useAuth()

  const [users, setUsers] = useState<MonitoredUser[]>([])
  const [usersLoading, setUsersLoading] = useState(true)
  const [usersError, setUsersError] = useState<string | null>(null)

  // ``selectedIds`` guarda el orden de selección; ``entries`` los datos de cada uno.
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [entries, setEntries] = useState<Entries>({})

  /** Actualiza un usuario seleccionado; si ya no lo está, no hace nada. */
  const patchEntry = useCallback(
    (telegramId: number, update: (entry: SelectedEntry) => SelectedEntry) => {
      setEntries((prev) => {
        const entry = prev[telegramId]
        return entry ? { ...prev, [telegramId]: update(entry) } : prev
      })
    },
    [],
  )

  const patchUser = useCallback((telegramId: number, patch: Partial<MonitoredUser>) => {
    setUsers((prev) => prev.map((u) => (u.telegramId === telegramId ? { ...u, ...patch } : u)))
  }, [])

  // --- Lista de usuarios (REST) --------------------------------------------

  // Cambiarlo vuelve a disparar la carga de usuarios (botón de recargar).
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    service
      .listUsers()
      .then((result) => {
        if (!cancelled) setUsers(result)
      })
      .catch((error: unknown) => {
        if (cancelled) return
        if (isSessionExpired(error)) void logout() // PrivateRoute redirige al login
        else setUsersError(errorMessage(error))
      })
      .finally(() => {
        if (!cancelled) setUsersLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [service, logout, reloadKey])

  const reloadUsers = () => {
    setUsersLoading(true)
    setUsersError(null)
    setReloadKey((key) => key + 1)
  }

  // --- Selección ------------------------------------------------------------

  const deselect = (telegramId: number) => {
    setSelectedIds((ids) => ids.filter((id) => id !== telegramId))
    setEntries((prev) => omit(prev, telegramId))
  }

  const clearSelection = () => {
    setSelectedIds([])
    setEntries({})
  }

  const toggleUser = (user: MonitoredUser) => {
    const telegramId = user.telegramId
    if (selectedIds.includes(telegramId)) {
      deselect(telegramId)
      return
    }

    setSelectedIds((ids) => [...ids, telegramId])
    setEntries((prev) => ({ ...prev, [telegramId]: { location: null, loading: true, error: null } }))

    // Última ubicación guardada. Si se deselecciona antes de que llegue,
    // ``patchEntry`` la descarta.
    service
      .getLastLocation(telegramId)
      .then((result) =>
        patchEntry(telegramId, (e) => ({ ...e, location: newest(e.location, result), loading: false })),
      )
      .catch((error: unknown) => {
        if (isSessionExpired(error)) {
          void logout()
          return
        }
        patchEntry(telegramId, (e) => ({ ...e, error: errorMessage(error), loading: false }))
      })
  }

  // --- Ubicación en vivo de los seleccionados (/ws, un socket por usuario) ---

  const { sync, statuses } = useWebSocketService({
    onError: (error) => {
      if (isSessionExpired(error)) void logout()
    },
  })

  const handleLiveEvent = useCallback(
    (event: LiveEvent) => {
      if (event.type === "location") {
        const incoming = event.location
        patchEntry(incoming.telegramId, (e) => ({
          ...e,
          location: newest(e.location, incoming),
          loading: false,
        }))
        patchUser(incoming.telegramId, { isLive: incoming.isLive, lastSeen: incoming.recordedAt })
        return
      }
      patchEntry(event.telegramId, (e) => (e.location ? { ...e, location: endLive(e.location) } : e))
      patchUser(event.telegramId, { isLive: false })
    },
    [patchEntry, patchUser],
  )

  // Abre los sockets de los recién seleccionados y cierra los que se quitaron;
  // los demás conservan su conexión. El hook maneja reconexión y token.
  useEffect(() => {
    sync(selectedIds, handleLiveEvent)
  }, [selectedIds, sync, handleLiveEvent])

  // --- Estado en vivo de TODOS (/ws/estado, un solo socket) -----------------

  const hasOpenedStatus = useRef(false)
  const handleStatusChange = (change: LiveStatusChange) => {
    if (!users.some((u) => u.telegramId === change.telegramId)) {
      reloadUsers() // usuario nuevo que aún no está en la lista
      return
    }
    patchUser(change.telegramId, { isLive: change.isLive })
    patchEntry(change.telegramId, (e) =>
      e.location
        ? {
            ...e,
            location: {
              ...e.location,
              isLive: change.isLive,
              liveUntil: change.isLive ? change.liveUntil : null,
            },
          }
        : e,
    )
  }
  useLiveStatusChannel({
    onChange: handleStatusChange,
    onOpen: () => {
      // La primera vez la lista ya se está cargando; al reconectar se recarga
      // para no perder cambios ocurridos mientras estaba desconectado.
      if (hasOpenedStatus.current) reloadUsers()
      hasOpenedStatus.current = true
    },
    onError: (error) => {
      if (isSessionExpired(error)) void logout()
    },
  })

  // Respaldo local: apaga el "En vivo" al llegar ``liveUntil`` aunque el
  // canal de estado esté caído. Un solo timer, para el próximo vencimiento.
  useEffect(() => {
    const deadlines = Object.values(entries)
      .map((e) => (e.location?.isLive && e.location.liveUntil ? Date.parse(e.location.liveUntil) : null))
      .filter((t): t is number => t !== null)
    if (deadlines.length === 0) return

    const timer = window.setTimeout(
      () => {
        const ids = expiredIds(entries, Date.now())
        for (const id of ids) {
          patchEntry(id, (e) => (e.location ? { ...e, location: endLive(e.location) } : e))
          patchUser(id, { isLive: false })
        }
      },
      Math.max(0, Math.min(...deadlines) - Date.now()),
    )
    return () => window.clearTimeout(timer)
  }, [entries, patchEntry, patchUser])

  // --- Render ---------------------------------------------------------------

  const titleOf = (telegramId: number) => {
    const user = users.find((u) => u.telegramId === telegramId)
    return user ? userLabel(user) : `Usuario ${telegramId}`
  }

  // Un marcador por seleccionado que ya tenga ubicación.
  const markers: MapMarker[] = selectedIds.flatMap((telegramId) => {
    const location = entries[telegramId]?.location
    if (!location) return []
    return [
      {
        telegramId,
        label: titleOf(telegramId),
        latitude: location.latitude,
        longitude: location.longitude,
        isLive: location.isLive,
        recordedAt: location.recordedAt,
      },
    ]
  })

  return (
    <div className="flex min-h-svh flex-col">
      <header className="flex items-center justify-between gap-4 border-b px-4 py-3">
        <h1 className="text-lg font-semibold">Bot de ubicaciones</h1>
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-muted-foreground sm:inline">{admin?.email}</span>
          <Button variant="outline" size="sm" onClick={() => void logout()}>
            <LogOutIcon />
            Cerrar sesión
          </Button>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-7xl flex-1 gap-4 p-4 md:grid-cols-[20rem_1fr] md:items-start">
        <UserList
          users={users}
          selectedIds={selectedIds}
          onToggle={toggleUser}
          onClearSelection={clearSelection}
          loading={usersLoading}
          error={usersError}
          onReload={reloadUsers}
        />

        {selectedIds.length === 0 ? (
          <LocationPanel title={null} location={null} />
        ) : (
          <div className="flex min-w-0 flex-col gap-4">
            <UsersMap markers={markers} />
            <div className="grid gap-4 lg:grid-cols-2">
              {selectedIds.map((telegramId) => {
                const entry = entries[telegramId]
                return (
                  <LocationPanel
                    key={telegramId}
                    title={titleOf(telegramId)}
                    location={entry?.location ?? null}
                    loading={entry?.loading ?? false}
                    error={entry?.error ?? null}
                    connection={statuses[telegramId]}
                    onClose={() => deselect(telegramId)}
                  />
                )
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
