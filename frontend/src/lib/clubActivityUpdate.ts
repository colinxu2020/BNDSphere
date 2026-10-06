export function changedRequiredText(value: string, original: string): string | undefined {
  const trimmed = value.trim();
  return trimmed === original ? undefined : trimmed;
}
