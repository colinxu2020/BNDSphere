import { client } from "./client";
import type { components } from "./schema";

export type UploadScene = components["schemas"]["UploadScene"];

type UploadOptions = {
  resizeImage?: boolean;
  maxWidth?: number;
  maxHeight?: number;
  quality?: number;
};

export async function uploadFile(
  file: File,
  scene: UploadScene,
  options: UploadOptions = {},
): Promise<string> {
  const uploadTarget = options.resizeImage
    ? await resizeImageFile(file, {
        maxWidth: options.maxWidth || 1600,
        maxHeight: options.maxHeight || 1200,
        quality: options.quality || 0.86,
      })
    : file;
  const contentType = uploadTarget.type || "application/octet-stream";
  const { data, error } = await client.POST("/api/v1/uploads/initiate", {
    body: {
      scene,
      filename: uploadTarget.name,
      content_type: contentType,
      size: uploadTarget.size,
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
    body: uploadTarget,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Upload failed with HTTP ${response.status}`);
  }

  const { data: confirmed, error: confirmError } = await client.POST("/api/v1/uploads/confirm", {
    body: {
      scene,
      object_key: data.object_key,
    },
  });

  if (confirmError) {
    throw confirmError;
  }
  if (!confirmed) {
    throw new Error("Upload confirmation response is empty.");
  }

  return confirmed.url;
}

async function resizeImageFile(
  file: File,
  options: Required<Pick<UploadOptions, "maxWidth" | "maxHeight" | "quality">>,
) {
  if (!file.type.startsWith("image/")) return file;

  const image = await loadImage(file);
  const ratio = Math.min(
    options.maxWidth / image.naturalWidth,
    options.maxHeight / image.naturalHeight,
    1,
  );
  const width = Math.max(1, Math.round(image.naturalWidth * ratio));
  const height = Math.max(1, Math.round(image.naturalHeight * ratio));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return file;

  context.drawImage(image, 0, 0, width, height);
  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, "image/webp", options.quality);
  });
  if (!blob) return file;

  return new File([blob], replaceExtension(file.name, "webp"), {
    type: "image/webp",
    lastModified: Date.now(),
  });
}

function loadImage(file: File) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("图片读取失败，请重新选择文件"));
    };
    image.src = url;
  });
}

function replaceExtension(filename: string, extension: string) {
  const safeName = filename || "poster";
  const dotIndex = safeName.lastIndexOf(".");
  const stem = dotIndex > 0 ? safeName.slice(0, dotIndex) : safeName;
  return `${stem}.${extension}`;
}
