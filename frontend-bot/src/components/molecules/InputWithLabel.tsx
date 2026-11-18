import type { ChangeEvent, ComponentProps, FocusEvent } from "react"
import {
  Controller,
  useFormContext,
  type FieldPath,
  type FieldValues,
} from "react-hook-form"

import { cn } from "@/lib/utils"
import { Field, FieldError, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { PasswordInput } from "@/components/molecules/PasswordInput"

type Props<T extends FieldValues> = {
  fieldTitle: string
  nameInSchema: FieldPath<T>
  classNameInput?: string
  classNameLabel?: string
  /** Oculta el label visualmente; sigue disponible para lectores de pantalla. */
  desactivarLabel?: boolean
} & Omit<ComponentProps<"input">, "name" | "value" | "defaultValue">

export function InputWithLabel<T extends FieldValues>({
  type = "text",
  fieldTitle,
  nameInSchema,
  classNameInput,
  classNameLabel,
  desactivarLabel,
  onChange,
  onBlur,
  onClick,
  ...props
}: Props<T>) {
  const { control } = useFormContext<T>()

  return (
    <Controller
      control={control}
      name={nameInSchema}
      render={({ field, fieldState }) => {
        // Los handlers del form siempre corren; los del padre se encadenan después.
        const inputProps = {
          ...props,
          ref: field.ref,
          name: field.name,
          id: nameInSchema,
          value: field.value ?? "",
          disabled: field.disabled ?? props.disabled,
          "aria-invalid": fieldState.invalid,
          className: cn("w-full", classNameInput),
          onChange: (e: ChangeEvent<HTMLInputElement>) => {
            field.onChange(e)
            onChange?.(e)
          },
          onBlur: (e: FocusEvent<HTMLInputElement>) => {
            field.onBlur()
            onBlur?.(e)
          },
        }

        return (
          <Field data-invalid={fieldState.invalid}>
            <FieldLabel
              htmlFor={nameInSchema}
              className={cn(desactivarLabel && "sr-only", classNameLabel)}
            >
              {fieldTitle}
            </FieldLabel>

            {type === "password" ? (
              <PasswordInput {...inputProps} />
            ) : (
              <Input
                {...inputProps}
                type={type}
                onClick={(e) => {
                  if (type === "date") e.currentTarget.showPicker?.()
                  onClick?.(e)
                }}
              />
            )}

            {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
          </Field>
        )
      }}
    />
  )
}
