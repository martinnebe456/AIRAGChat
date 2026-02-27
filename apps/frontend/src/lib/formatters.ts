export function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

export function truncate(value: string, max = 120) {
  if (value.length <= max) return value;
  return `${value.slice(0, max)}...`;
}

