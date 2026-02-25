import { cn } from "@/lib/utils";

interface LoadingSkeletonProps {
  className?: string;
}

/**
 * A reusable loading skeleton component for pulse animations.
 */
export default function LoadingSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-neutral-200 dark:bg-neutral-800",
        className
      )}
    />
  );
}
