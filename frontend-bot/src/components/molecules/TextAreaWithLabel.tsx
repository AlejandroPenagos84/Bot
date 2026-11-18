import type { ComponentProps } from "react"
import {
  Controller,
  useFormContext,
  type FieldPath,
  type FieldValues,
} from "react-hook-form"

import { cn } from "@/lib/utils"
import { Field, FieldError, FieldLabel } from "@/components/ui/field"
import { Textarea } from "@/components/ui/textarea"

type Props<T extends FieldValues> = {
  fieldTitle: string
  nameInSchema: FieldPath<T>
  classNameInput?: string
  classNameLabel?: string
} & Omit<ComponentProps<"textarea">, "name" | "value" | "defaultValue">

export function TextAreaWithLabel<T extends FieldValues>({
  fieldTitle,
  nameInSchema,
  classNameInput,
  classNameLabel,
  onChange,
  onBlur,
  ...props
}: Props<T>) {
  const { control } = useFormContext<T>()

  return (
    <Controller
      control={control}
      name={nameInSchema}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel htmlFor={nameInSchema} className={classNameLabel}>
            {fieldTitle}
          </FieldLabel>

          <Textarea
            {...props}
            ref={field.ref}
            name={field.name}
            id={nameInSchema}
            value={field.value ?? ""}
            disabled={field.disabled ?? props.disabled}
            aria-invalid={fieldState.invalid}
            className={cn("w-full", classNameInput)}
            onChange={(e) => {
              field.onChange(e)
              onChange?.(e)
            }}
            onBlur={(e) => {
              field.onBlur()
              onBlur?.(e)
            }}
          />

          {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
        </Field>
      )}
    />
  )
}
