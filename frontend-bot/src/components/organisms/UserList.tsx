import { CheckIcon, RefreshCwIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { LiveBadge } from "@/components/molecules/LiveBadge"
import { userLabel } from "@/lib/users"
import type { MonitoredUser } from "@/services/users/UsersService"

interface UserListProps {
  users: MonitoredUser[]
  /** Usuarios seleccionados (se pueden elegir varios). */
  selectedIds: readonly number[]
  /** Selecciona o deselecciona un usuario. */
  onToggle: (user: MonitoredUser) => void
  onClearSelection?: () => void
  loading?: boolean
  error?: string | null
  onReload?: () => void
}

export function UserList({
  users,
  selectedIds,
  onToggle,
  onClearSelection,
  loading = false,
  error = null,
  onReload,
}: UserListProps) {
  const selected = new Set(selectedIds)

  return (
    <section className="flex min-h-0 flex-col rounded-xl border bg-card">
      <header className="flex items-center justify-between gap-2 border-b px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold">
            Usuarios <span className="font-normal text-muted-foreground">({users.length})</span>
          </h2>
          {selected.size > 0 && (
            <p className="text-xs text-muted-foreground">
              {selected.size} {selected.size === 1 ? "seleccionado" : "seleccionados"}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1">
          {onClearSelection && selected.size > 0 && (
            <Button variant="ghost" size="sm" onClick={onClearSelection}>
              Limpiar
            </Button>
          )}
          {onReload && (
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Recargar usuarios"
              onClick={onReload}
              disabled={loading}
            >
              <RefreshCwIcon className={cn(loading && "animate-spin")} />
            </Button>
          )}
        </div>
      </header>

      {error ? (
        <p role="alert" className="p-4 text-sm text-destructive">
          {error}
        </p>
      ) : loading && users.length === 0 ? (
        <p className="p-4 text-sm text-muted-foreground">Cargando usuarios…</p>
      ) : users.length === 0 ? (
        <p className="p-4 text-sm text-muted-foreground">No hay usuarios registrados.</p>
      ) : (
        <ul className="flex-1 overflow-y-auto p-2" aria-label="Usuarios">
          {users.map((user) => {
            const isSelected = selected.has(user.telegramId)
            return (
              <li key={user.telegramId}>
                <button
                  type="button"
                  onClick={() => onToggle(user)}
                  aria-pressed={isSelected}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors",
                    "outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50",
                    isSelected && "bg-muted",
                  )}
                >
                  <span
                    aria-hidden
                    className={cn(
                      "flex size-5 shrink-0 items-center justify-center rounded-md border transition-colors",
                      isSelected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input bg-background",
                    )}
                  >
                    {isSelected && <CheckIcon className="size-3.5" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{userLabel(user)}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      ID {user.telegramId}
                    </span>
                  </span>
                  <LiveBadge live={user.isLive} />
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
