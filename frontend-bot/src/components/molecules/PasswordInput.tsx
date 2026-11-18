import { useState, type ComponentProps } from "react"
import { EyeIcon, EyeOffIcon } from "lucide-react"

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"

type PasswordInputProps = Omit<ComponentProps<"input">, "type">

function PasswordInput({
  className,
  autoComplete = "current-password",
  ...props
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false)

  return (
    <InputGroup className={className}>
      <InputGroupInput
        {...props}
        type={visible ? "text" : "password"}
        autoComplete={autoComplete}
      />
      <InputGroupAddon align="inline-end">
        <InputGroupButton
          size="icon-xs"
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
          aria-pressed={visible}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? <EyeOffIcon /> : <EyeIcon />}
        </InputGroupButton>
      </InputGroupAddon>
    </InputGroup>
  )
}

export { PasswordInput }
