import { Navigate, useLocation, useNavigate, type Location } from "react-router"

import { LoginForm, type LoginFormValues } from "@/components/organisms/LoginForm"
import { useAuth } from "@/hooks/useAuth"
import { AuthError } from "@/services/auth/AuthService"

const ERROR_MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: "Correo o contraseña incorrectos",
  ACCOUNT_DISABLED: "La cuenta está deshabilitada",
  ACCOUNT_NOT_VERIFIED: "La cuenta no está verificada",
  NETWORK_ERROR: "No se pudo conectar con el servidor",
  VALIDATION_ERROR: "Revisa los datos ingresados",
}

function toFriendlyMessage(error: unknown): string {
  if (error instanceof AuthError) {
    return ERROR_MESSAGES[error.code] ?? "No se pudo iniciar sesión. Intenta de nuevo."
  }
  return "Ocurrió un error inesperado"
}

export default function LoginPage() {
  const { login, status } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Ruta a la que se quería entrar antes de ser redirigido (la guarda PrivateRoute).
  const from = (location.state as { from?: Location } | null)?.from?.pathname ?? "/"

  if (status === "authenticated") {
    return <Navigate to={from} replace />
  }

  const handleLogin = async (values: LoginFormValues) => {
    try {
      await login(values)
      navigate(from, { replace: true })
    } catch (error) {
      throw new Error(toFriendlyMessage(error))
    }
  }

  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <section className="w-full max-w-sm rounded-xl border bg-card p-6 shadow-sm">
        <header className="mb-6 flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">Iniciar sesión</h1>
          <p className="text-sm text-muted-foreground">
            Ingresa con tu cuenta de administrador
          </p>
        </header>

        <LoginForm onSubmit={handleLogin} />
      </section>
    </main>
  )
}
