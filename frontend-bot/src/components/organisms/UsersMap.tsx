import { useEffect, useMemo } from "react"
import { divIcon, latLngBounds } from "leaflet"
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet"
import "leaflet/dist/leaflet.css"

import { cn } from "@/lib/utils"
import { LiveBadge } from "@/components/molecules/LiveBadge"

export interface MapMarker {
  telegramId: number
  label: string
  latitude: number
  longitude: number
  isLive: boolean
  /** Fecha (ISO) de la ubicación. */
  recordedAt: string
}

interface UsersMapProps {
  markers: MapMarker[]
  className?: string
}

// Vista inicial cuando aún no hay marcadores (Colombia).
const DEFAULT_CENTER: [number, number] = [4.6, -74.08]
const DEFAULT_ZOOM = 5
const SINGLE_MARKER_ZOOM = 15

const dateFormat = new Intl.DateTimeFormat("es-CO", { dateStyle: "short", timeStyle: "medium" })

/** Pin en HTML: verde y latiendo si está en vivo, gris si no. */
function pinIcon(live: boolean) {
  const color = live ? "bg-emerald-500" : "bg-zinc-400"
  return divIcon({
    className: "", // sin el fondo blanco por defecto de Leaflet
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
    html: `
      <span class="relative flex size-6 items-center justify-center">
        ${live ? `<span class="absolute inline-flex size-full animate-ping rounded-full ${color} opacity-60"></span>` : ""}
        <span class="relative inline-flex size-4 rounded-full border-2 border-white shadow-md ${color}"></span>
      </span>`,
  })
}

const LIVE_ICON = pinIcon(true)
const IDLE_ICON = pinIcon(false)

/**
 * Encuadra el mapa cuando cambia QUÉ usuarios se muestran, no cuando se
 * mueven: así el mapa no salta con cada actualización en vivo.
 */
function FitToMarkers({ markers }: { markers: MapMarker[] }) {
  const map = useMap()
  const idsKey = markers.map((m) => m.telegramId).sort((a, b) => a - b).join(",")

  useEffect(() => {
    if (markers.length === 0) return
    if (markers.length === 1) {
      map.setView([markers[0].latitude, markers[0].longitude], SINGLE_MARKER_ZOOM)
      return
    }
    const bounds = latLngBounds(markers.map((m) => [m.latitude, m.longitude]))
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: SINGLE_MARKER_ZOOM })
    // Solo se re-encuadra al cambiar el conjunto de usuarios (idsKey).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, idsKey])

  return null
}

export function UsersMap({ markers, className }: UsersMapProps) {
  const sorted = useMemo(
    // Los que están en vivo se dibujan encima.
    () => [...markers].sort((a, b) => Number(a.isLive) - Number(b.isLive)),
    [markers],
  )

  return (
    <section
      className={cn("relative isolate overflow-hidden rounded-xl border bg-card", className)}
      aria-label="Mapa de ubicaciones"
    >
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        scrollWheelZoom
        className="h-80 w-full md:h-[28rem]"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {sorted.map((m) => (
          <Marker
            key={m.telegramId}
            position={[m.latitude, m.longitude]}
            icon={m.isLive ? LIVE_ICON : IDLE_ICON}
            zIndexOffset={m.isLive ? 1000 : 0}
            title={m.label}
          >
            <Popup>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <strong className="text-sm">{m.label}</strong>
                  <LiveBadge live={m.isLive} />
                </div>
                <span className="font-mono text-xs">
                  {m.latitude.toFixed(6)}, {m.longitude.toFixed(6)}
                </span>
                <span className="text-xs text-muted-foreground">
                  {dateFormat.format(new Date(m.recordedAt))}
                </span>
              </div>
            </Popup>
          </Marker>
        ))}
        <FitToMarkers markers={markers} />
      </MapContainer>

      {markers.length === 0 && (
        <div className="pointer-events-none absolute inset-0 z-[1000] flex items-center justify-center">
          <p className="rounded-lg bg-background/90 px-3 py-2 text-sm text-muted-foreground shadow-sm">
            Ninguno de los seleccionados tiene ubicación registrada.
          </p>
        </div>
      )}
    </section>
  )
}
