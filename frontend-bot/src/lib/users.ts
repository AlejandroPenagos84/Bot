import type { MonitoredUser } from "@/services/users/UsersService"

/** Nombre visible de un usuario: su teléfono o, si no lo dio, su ID de Telegram. */
export function userLabel(user: MonitoredUser): string {
  return user.phone ?? `Usuario ${user.telegramId}`
}
