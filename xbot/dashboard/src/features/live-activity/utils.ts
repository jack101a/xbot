import { formatISTDateTime } from "@/lib/time";

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatFullDate(isoStr?: string | null): string {
  return formatISTDateTime(isoStr);
}
