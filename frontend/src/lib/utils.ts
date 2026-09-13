import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Only http(s) URLs may be rendered as clickable links. Stored fields such as
 * proof_files historically accepted arbitrary strings, so javascript:/data:
 * pseudo-protocol links could persist; never hand them to <a href>.
 */
export function isRenderableLinkUrl(url: string): boolean {
  return /^https?:\/\//i.test(url);
}
