/**
 * Utility functions for parsing UTC timestamps and formatting in Indian Standard Time (IST - Asia/Kolkata).
 */

export function parseUtcDate(isoStr?: string | null): Date | null {
  if (!isoStr) return null;
  const str = String(isoStr).trim();
  if (!str) return null;
  // If string has no timezone indicator (no 'Z' and no +XX:XX / -XX:XX), append 'Z' to treat as UTC
  const hasTz = str.endsWith("Z") || /[+-]\d{2}(?::?\d{2})?$/.test(str);
  const normalized = hasTz ? str : str + "Z";
  const d = new Date(normalized);
  return isNaN(d.getTime()) ? new Date(str) : d;
}

export function formatISTTime(isoStr?: string | null, includeSeconds = false): string {
  const d = parseUtcDate(isoStr);
  if (!d) return "";
  return d.toLocaleTimeString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    second: includeSeconds ? "2-digit" : undefined,
    hour12: true,
  });
}

export function formatISTDateTime(isoStr?: string | null): string {
  const d = parseUtcDate(isoStr);
  if (!d) return "";
  return d.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}
