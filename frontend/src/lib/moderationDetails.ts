export function moderationDetails(
  fields: string[] | undefined,
  rows: [string, string, unknown][],
): [string, unknown][] {
  // Match build_update_payload, including its fallback for legacy requests.
  return rows
    .filter(([field, , value]) => (fields?.length ? fields.includes(field) : value != null))
    .map(([, label, value]) => [label, value == null || value === "" ? "清空" : value]);
}
