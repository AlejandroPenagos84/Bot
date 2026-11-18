import { FormProvider, useForm, type FieldErrors, type Resolver, type ResolverResult } from "react-hook-form"
import { LoaderCircleIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { FieldError, FieldGroup } from "@/components/ui/field"
import { InputWithLabel } from "@/components/molecules/InputWithLabel"
import type { LoginCredentials } from "@/services/auth/AuthService"

export type LoginFormValues = LoginCredentials

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Validación local: evita enviar el formulario vacío o con un correo mal formado. */
const loginResolver: Resolver<LoginFormValues> = (values): ResolverResult<LoginFormValues> => {
  const errors: FieldErrors<LoginFormValues> = {}
  const email = values.email.trim()

  if (!email) {
    errors.email = { type: "required", message: "El correo es obligatorio" }
  } else if (!EMAIL_PATTERN.test(email)) {
    errors.email = { type: "pattern", message: "Ingresa un correo válido" }
  }

  if (!values.password) {
    errors.password = { type: "required", message: "La contraseña es obligatoria" }
  }

  if (Object.keys(errors).length > 0) {
    return { values: {}, errors }
  }
  return { values: { email, password: values.password }, errors: {} }
}

interface LoginFormProps {
  /** Recibe credenciales ya validadas. Si lanza un error, se muestra en el formulario. */
  onSubmit: (values: LoginFormValues) => Promise<void>
}

export function LoginForm({ onSubmit }: LoginFormProps) {
  const form = useForm<LoginFormValues>({
    defaultValues: { email: "", password: "" },
    resolver: loginResolver,
    mode: "onTouched",
  })

  const {
    handleSubmit,
    setError,
    formState: { isSubmitting, errors },
  } = form

  const submit = handleSubmit(async (values) => {
    try {
      await onSubmit(values)
    } catch (error) {
      setError("root", {
        message: error instanceof Error ? error.message : "No se pudo iniciar sesión",
      })
    }
  })

  return (
    <FormProvider {...form}>
      <form onSubmit={submit} noValidate className="flex flex-col gap-6">
        <FieldGroup>
          <InputWithLabel<LoginFormValues>
            fieldTitle="Correo electrónico"
            nameInSchema="email"
            type="email"
            autoComplete="email"
            placeholder="admin@ejemplo.com"
            autoFocus
          />
          <InputWithLabel<LoginFormValues>
            fieldTitle="Contraseña"
            nameInSchema="password"
            type="password"
            autoComplete="current-password"
          />
        </FieldGroup>

        {errors.root && <FieldError errors={[errors.root]} />}

        <Button type="submit" size="lg" disabled={isSubmitting} className="w-full">
          {isSubmitting && <LoaderCircleIcon className="animate-spin" />}
          {isSubmitting ? "Ingresando…" : "Iniciar sesión"}
        </Button>
      </form>
    </FormProvider>
  )
}
