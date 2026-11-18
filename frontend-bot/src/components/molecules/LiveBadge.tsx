import { cn } from "@/lib/utils"

interface LiveBadgeProps {
  live: boolean
  className?: string
}

/** Indicador "En vivo" / "Sin conexión" con un punto que late cuando está activo. */
export function LiveBadge({ live, className }: LiveBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
        live
          ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
          : "bg-muted text-muted-foreground",
        className,
      )}
    >
      <span className="relative flex size-2">
        {live && (
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-500 opacity-75" />
        )}
        <span
          className={cn(
            "relative inline-flex size-2 rounded-full",
            live ? "bg-emerald-500" : "bg-muted-foreground/50",
          )}
        />
      </span>
      {live ? "En vivo" : "Sin conexión"}
    </span>
  )
}
