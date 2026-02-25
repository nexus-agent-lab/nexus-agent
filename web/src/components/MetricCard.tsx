import { cn } from "@/lib/utils";
import { ArrowUpIcon, ArrowDownIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
  icon?: React.ReactNode;
}

/**
 * A reusable card for displaying metrics (label, value, delta).
 */
export default function MetricCard({
  label,
  value,
  delta,
  className,
  icon,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
          {label}
        </p>
        {icon && (
          <div className="text-neutral-400 dark:text-neutral-500">{icon}</div>
        )}
      </div>
      <div className="mt-2 flex items-baseline justify-between">
        <h3 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
          {value}
        </h3>
        {delta && (
          <div
            className={cn(
              "flex items-center text-sm font-medium",
              delta.isPositive
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-rose-600 dark:text-rose-400"
            )}
          >
            {delta.isPositive ? (
              <ArrowUpIcon className="mr-1 h-4 w-4" />
            ) : (
              <ArrowDownIcon className="mr-1 h-4 w-4" />
            )}
            {delta.value}%
          </div>
        )}
      </div>
    </div>
  );
}
