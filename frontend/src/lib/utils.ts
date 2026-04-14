import type { ClassValue } from 'clsx';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 格式化 API 错误信息，包含错误编码和原因
 * @param error API 返回的错误对象
 * @param defaultMessage 默认错误信息
 */
export function formatError(error: any, defaultMessage: string = '操作失败'): string {
  if (!error) return defaultMessage;

  // 尝试从不同的结构中提取错误信息
  // FastAPI 常见的错误结构是 { detail: ... } 或 { message: ... }
  const detail =
    error.detail || error.message || error.response?.data?.detail || error.response?.data?.message;
  const status = error.status || error.response?.status;

  if (detail) {
    const errorDetail = typeof detail === 'string' ? detail : JSON.stringify(detail);
    return status ? `错误 [${status}]: ${errorDetail}` : errorDetail;
  }

  // 如果没有明确的 detail，但有 status
  if (status) {
    return `错误 [${status}]: ${defaultMessage}`;
  }

  // 兜底返回字符串形式的错误
  if (typeof error === 'string') return error;

  return defaultMessage;
}
