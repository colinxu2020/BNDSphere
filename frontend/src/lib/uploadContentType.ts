const IMAGE_CONTENT_TYPES = new Map([
  ["jpg", "image/jpeg"],
  ["jpeg", "image/jpeg"],
  ["png", "image/png"],
  ["webp", "image/webp"],
]);

export function uploadContentType(file: Pick<File, "name" | "type">): string {
  if (file.type && file.type !== "application/octet-stream") return file.type;

  // Some browsers cannot infer MIME from the local file. This is a metadata
  // fallback only; the server still enforces each upload scene's policy.
  const extension = file.name.includes(".") ? file.name.split(".").at(-1)?.toLowerCase() : "";
  return IMAGE_CONTENT_TYPES.get(extension ?? "") ?? "application/octet-stream";
}
