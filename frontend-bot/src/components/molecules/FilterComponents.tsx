import { useId, useState, type ReactNode } from "react"
import { AnimatePresence, motion } from "motion/react"
import {
  ChevronDown,
  Plus,
  SlidersHorizontal,
  type LucideIcon,
} from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const LABEL = "text-xs font-medium text-muted-foreground"
const CONTROL = "bg-muted/60"

type FieldProps = {
  label: string
  value: string
  onChange: (value: string) => void
}

export function FilterField({
  label,
  placeholder,
  value,
  onChange,
}: FieldProps & { placeholder: string }) {
  const id = useId()
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id} className={LABEL}>
        {label}
      </Label>
      <Input
        id={id}
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={CONTROL}
      />
    </div>
  )
}

export function FilterDate({ label, value, onChange }: FieldProps) {
  const id = useId()
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id} className={LABEL}>
        {label}
      </Label>
      <Input
        id={id}
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onClick={(e) => e.currentTarget.showPicker?.()}
        className={CONTROL}
      />
    </div>
  )
}

type Option = { value: string; label: string }

export function SelectField({
  label,
  options,
  value,
  onChange,
  placeholder = "Selecciona…",
}: FieldProps & { options: Option[]; placeholder?: string }) {
  const id = useId()
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id} className={LABEL}>
        {label}
      </Label>
      <Select
        items={options}
        value={value || null}
        onValueChange={(v) => onChange(v ?? "")}
      >
        <SelectTrigger id={id} className={cn("w-full", CONTROL)}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

const URGENCY_CLASS = {
  red: "text-destructive",
  amber: "text-amber-500",
  green: "text-emerald-500",
} as const

export function InfoRow({
  label,
  value,
  urgency,
}: {
  label: string
  value: string
  urgency?: keyof typeof URGENCY_CLASS
}) {
  return (
    <div className="flex justify-between gap-4 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span
        className={cn(
          "font-semibold",
          urgency ? cn("font-bold", URGENCY_CLASS[urgency]) : "text-foreground"
        )}
      >
        {value}
      </span>
    </div>
  )
}

export function EmptyState({
  icon: Icon,
  title,
  subtitle,
  action,
  onAction,
  actionIcon: ActionIcon = Plus,
  visibleButton = false,
}: {
  icon: LucideIcon
  title: string
  subtitle: string
  action?: string
  onAction?: () => void
  actionIcon?: LucideIcon
  visibleButton?: boolean
}) {
  return (
    <div className="mt-6 rounded-xl bg-card p-12 text-center text-card-foreground shadow-lg">
      <div className="mx-auto mb-6 flex size-20 items-center justify-center rounded-full bg-muted">
        <Icon size={40} className="text-muted-foreground" />
      </div>
      <h3 className="mb-2 text-xl font-bold">{title}</h3>
      <p className="mb-6 text-muted-foreground">{subtitle}</p>
      {visibleButton && action && onAction && (
        <Button size="lg" onClick={onAction} className="px-8">
          <ActionIcon data-icon="inline-start" />
          {action}
        </Button>
      )}
    </div>
  )
}

export function FilterPanel({
  activeCount,
  children,
}: {
  activeCount: number
  children: ReactNode
}) {
  const [expanded, setExpanded] = useState(false)
  const contentId = useId()

  return (
    <div className="mb-6 rounded-xl bg-card text-card-foreground shadow-lg">
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={contentId}
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between rounded-xl px-6 py-4 transition-colors outline-none hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <span className="flex items-center gap-2.5">
          <SlidersHorizontal size={18} className="text-muted-foreground" />
          <span className="text-sm font-semibold">Filtros</span>
          {activeCount > 0 && (
            <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-[11px] font-bold text-primary-foreground">
              {activeCount}
            </span>
          )}
        </span>
        <motion.span
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="flex"
        >
          <ChevronDown size={18} className="text-muted-foreground" />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id={contentId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-6 pb-6">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
