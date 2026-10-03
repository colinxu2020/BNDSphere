import type { Root } from "hast";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import { visit } from "unist-util-visit";

export function markdownLengthError(value: string, maxLength: number): string | null {
  return value.length > maxLength ? `内容最多 ${maxLength} 字（包含 Markdown 标记）。` : null;
}

export function rehypeSanitizeWithFragments(namespace: string) {
  const prefix = `${defaultSchema.clobberPrefix}${namespace}-`;
  const sanitize = rehypeSanitize({ ...defaultSchema, clobberPrefix: prefix });
  return (tree: Root) => {
    const sanitized = sanitize(tree);
    const ids = new Set<string>();
    visit(sanitized, "element", (node) => {
      if (typeof node.properties.id === "string") ids.add(node.properties.id);
    });

    visit(sanitized, "element", (node) => {
      const href = node.properties.href;
      if (typeof href !== "string" || !href.startsWith("#")) return;
      const fragment = href.slice(1);
      let id: string;
      try {
        id = decodeURIComponent(fragment);
      } catch {
        return;
      }
      // Keep sanitize's DOM clobbering protection and point at the renamed target.
      if (ids.has(prefix + id)) node.properties.href = `#${prefix}${fragment}`;
    });
    return sanitized;
  };
}
