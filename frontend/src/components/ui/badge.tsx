import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-emerald-100 text-emerald-800 hover:bg-emerald-200/80",
        secondary:
          "border-transparent bg-amber-100 text-amber-800 hover:bg-amber-200/80",
        destructive:
          "border-transparent bg-rose-100 text-rose-800 hover:bg-rose-200/80",
        outline: "text-foreground border-slate-200",
        mint: "border-emerald-200/60 bg-emerald-50 text-emerald-700 font-medium",
        gold: "border-amber-200/60 bg-amber-50 text-amber-800 font-medium",
        slate: "border-slate-200 bg-slate-100 text-slate-700 font-medium",
        positive: "border-emerald-200 bg-emerald-50 text-emerald-700 font-medium",
        negative: "border-rose-200 bg-rose-50 text-rose-700 font-medium"
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
