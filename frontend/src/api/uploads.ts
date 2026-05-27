import { client } from "./client";
import type { components } from "./schema";

const PUBLIC_BUCKET_BASE =
  "https://r2.pulldown.dev";

export type UploadScene = components["schemas"]["UploadScene"];

export async function uploadFile(
  file: File,
  scene: UploadScene,
): Promise<string> {
  const contentType = file.type || "application/octet-stream";
  const { data, error } = await client.POST("/api/v1/uploads/initiate", {
    body: {
      scene,
      filename: file.name,
      content_type: contentType,
      size: file.size,
    },
  });

  if (error) {
    throw error;
  }

  if (!data) {
    throw new Error("Upload initiate response is empty.");
  }

  const response = await fetch(data.upload_url, {
    method: "PUT",
    headers: {
      "Content-Type": contentType,
    },
    body: file,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Upload failed with HTTP ${response.status}`);
  }

  return `${PUBLIC_BUCKET_BASE}/${data.object_key}`;
}
