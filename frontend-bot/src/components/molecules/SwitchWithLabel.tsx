import {
  Controller,
  useFormContext,
  type FieldPath,
  type FieldValues,
} from "react-hook-form"

import { Field, FieldError, FieldLabel } from "@/components/ui/field"
import { Switch } from "@/components/ui/switch"

type Props<T extends FieldValues> = {
  fieldTitle: string
  nameInSchema: FieldPath<T>
  classNameLabel?: string
}

export function SwitchWithLabel<T extends FieldValues>({
  fieldTitle,
  nameInSchema,
  classNameLabel,
}: Props<T>) {
  const { control } = useFormContext<T>()

  return (
    <Controller
      control={control}
      name={nameInSchema}
      render={({ field, fieldState }) => (
        <Field orientation="horizontal" data-invalid={fieldState.invalid}>
          <Switch
            id={nameInSchema}
            name={field.name}
            inputRef={field.ref}
            checked={Boolean(field.value)}
            onCheckedChange={(checked) => field.onChange(checked)}
            onBlur={field.onBlur}
            disabled={field.disabled}
            aria-invalid={fieldState.invalid}
          />
          <FieldLabel htmlFor={nameInSchema} className={classNameLabel}>
            {fieldTitle}
          </FieldLabel>

          {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
        </Field>
      )}
    />
  )
}
