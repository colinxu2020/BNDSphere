import { Fragment, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import privacyPolicy from "../legal/privacy-policy.md?raw";
import userAgreement from "../legal/user-agreement.md?raw";
import crossBorderTransferConsent from "../legal/cross-border-transfer-consent.md?raw";

const documents = {
  "privacy-policy": privacyPolicy,
  "user-agreement": userAgreement,
  "cross-border-transfer-consent": crossBorderTransferConsent,
} as const;

export function LegalDocument() {
  const { document } = useParams();
  const markdown =
    document && document in documents ? documents[document as keyof typeof documents] : null;

  if (!markdown) {
    return (
      <div className="mx-auto flex min-h-[50vh] max-w-xl flex-col items-center justify-center gap-4 text-center">
        <h1 className="text-2xl font-bold text-slate-900">未找到该合规文件</h1>
        <Link to="/register" className="font-semibold text-primary-600 hover:underline">
          返回注册页面
        </Link>
      </div>
    );
  }

  return (
    <article className="mx-auto w-full max-w-4xl rounded-md border border-slate-200 bg-white px-6 py-8 shadow-sm sm:px-10 sm:py-12">
      <MarkdownDocument markdown={markdown} />
    </article>
  );
}

function MarkdownDocument({ markdown }: { markdown: string }) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];

  for (let index = 0; index < lines.length;) {
    const line = lines[index].trim();

    if (!line) {
      index += 1;
      continue;
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      const className =
        level === 1
          ? "mb-6 mt-10 text-2xl font-bold text-slate-950 first:mt-0 sm:text-3xl"
          : level === 2
            ? "mb-4 mt-8 text-xl font-bold text-slate-900"
            : level === 3
              ? "mb-3 mt-6 text-lg font-semibold text-slate-900"
              : "mb-2 mt-5 font-semibold text-slate-800";
      const children = renderInline(heading[2], `heading-${index}`);
      blocks.push(
        level === 1 ? (
          <h1 key={index} className={className}>
            {children}
          </h1>
        ) : level === 2 ? (
          <h2 key={index} className={className}>
            {children}
          </h2>
        ) : level === 3 ? (
          <h3 key={index} className={className}>
            {children}
          </h3>
        ) : (
          <h4 key={index} className={className}>
            {children}
          </h4>
        ),
      );
      index += 1;
      continue;
    }

    if (/^-{3,}$/.test(line)) {
      blocks.push(<hr key={index} className="my-8 border-slate-200" />);
      index += 1;
      continue;
    }

    const unorderedItem = /^[-*]\s+(.+)$/.exec(line);
    if (unorderedItem) {
      const items: ReactNode[] = [];
      while (index < lines.length) {
        const item = /^[-*]\s+(.+)$/.exec(lines[index].trim());
        if (!item) break;
        items.push(<li key={index}>{renderInline(item[1], `unordered-${index}`)}</li>);
        index += 1;
      }
      blocks.push(
        <ul key={`list-${index}`} className="mb-4 list-disc space-y-1 pl-6 text-slate-700">
          {items}
        </ul>,
      );
      continue;
    }

    const orderedItem = /^\d+\.\s+(.+)$/.exec(line);
    if (orderedItem) {
      const items: ReactNode[] = [];
      while (index < lines.length) {
        const item = /^\d+\.\s+(.+)$/.exec(lines[index].trim());
        if (!item) break;
        items.push(<li key={index}>{renderInline(item[1], `ordered-${index}`)}</li>);
        index += 1;
      }
      blocks.push(
        <ol key={`list-${index}`} className="mb-4 list-decimal space-y-1 pl-6 text-slate-700">
          {items}
        </ol>,
      );
      continue;
    }

    blocks.push(
      <p key={index} className="mb-4 leading-7 text-slate-700">
        {renderInline(line, `paragraph-${index}`)}
      </p>,
    );
    index += 1;
  }

  return blocks;
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const pattern = /(\*\*.+?\*\*|`.+?`|\[[^\]]+\]\([^)]+\))/g;
  let cursor = 0;

  for (const match of text.matchAll(pattern)) {
    const start = match.index ?? 0;
    if (start > cursor) parts.push(text.slice(cursor, start));

    const token = match[0];
    const key = `${keyPrefix}-${start}`;
    if (token.startsWith("**")) {
      parts.push(<strong key={key}>{renderInline(token.slice(2, -2), `${key}-strong`)}</strong>);
    } else if (token.startsWith("`")) {
      parts.push(
        <code key={key} className="rounded bg-slate-100 px-1.5 py-0.5 text-sm text-slate-800">
          {token.slice(1, -1)}
        </code>,
      );
    } else {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      if (link) {
        parts.push(
          <a key={key} href={link[2]} className="font-medium text-primary-600 hover:underline">
            {link[1]}
          </a>,
        );
      }
    }

    cursor = start + token.length;
  }

  if (cursor < text.length) parts.push(text.slice(cursor));
  return parts.map((part, index) => <Fragment key={`${keyPrefix}-part-${index}`}>{part}</Fragment>);
}
