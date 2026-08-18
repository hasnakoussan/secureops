import type { ReactNode } from "react";

type AlertVariant = "error" | "success" | "info" | "warning";

const VARIANT_STYLES: Record<AlertVariant, string> = {
  error: "text-[var(--color-risk-critical)] bg-[var(--color-risk-critical)]/10",
  success: "text-[var(--color-risk-safe)] bg-[var(--color-risk-safe)]/10",
  warning: "text-[var(--color-risk-warning)] bg-[var(--color-risk-warning)]/10",
  info: "text-[var(--color-text-muted)] bg-[var(--color-surface)]",
};

interface AlertProps {
  variant: AlertVariant;
  children: ReactNode;
}

/**
 * Bandeau de message, réutilisé partout où on affichait auparavant un
 * <p> dupliqué avec les mêmes classes Tailwind. Centraliser ici évite
 * la dérive visuelle (un message d'erreur avec une teinte légèrement
 * différente d'une page à l'autre par oubli de copier-coller).
 */
export function Alert({ variant, children }: AlertProps) {
  return (
    <p role={variant === "error" ? "alert" : "status"} className={`text-sm rounded-md px-3 py-2 ${VARIANT_STYLES[variant]}`}>
      {children}
    </p>
  );
}
