import { motion } from "motion/react";
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useRef, useState } from "react";
import { Check, QrCode, Share3, X } from "./Icons";
import { StatusMessage } from "./AppPrimitives";

export function ClubShareDialog({
  clubName,
  shareUrl,
  onClose,
}: {
  clubName: string;
  shareUrl: string;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const qrCodeRef = useRef<SVGSVGElement>(null);
  const [isLinkCopied, setIsLinkCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const previousFocus = document.activeElement;
    dialog.showModal();
    closeButtonRef.current?.focus({ preventScroll: true });

    return () => {
      dialog.close();
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) {
        previousFocus.focus({ preventScroll: true });
      }
    };
  }, []);

  useEffect(() => {
    if (!isLinkCopied) return;
    const timer = window.setTimeout(() => setIsLinkCopied(false), 2200);
    return () => window.clearTimeout(timer);
  }, [isLinkCopied]);

  const copyShareLink = async () => {
    setCopyError(null);
    setIsLinkCopied(false);
    try {
      await navigator.clipboard.writeText(shareUrl);
      setIsLinkCopied(true);
    } catch {
      setCopyError("复制链接失败，请稍后重试");
    }
  };

  const downloadQrCode = () => {
    const svg = qrCodeRef.current;
    if (!svg) return;

    const blob = new Blob([new XMLSerializer().serializeToString(svg)], {
      type: "image/svg+xml;charset=utf-8",
    });
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `${clubName || "社团"}-二维码.svg`;
    dialogRef.current?.append(link);
    try {
      link.click();
    } finally {
      // Let the browser consume the URL, even if the dialog closes immediately.
      window.setTimeout(() => {
        link.remove();
        URL.revokeObjectURL(downloadUrl);
      }, 1000);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="club-share-title"
      aria-describedby="club-share-description"
      className="fixed inset-0 m-0 h-full max-h-none w-full max-w-none items-center justify-center border-0 bg-transparent p-4 backdrop:bg-slate-950/45 backdrop:backdrop-blur-sm open:flex"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          event.preventDefault();
          onClose();
        }
      }}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const buttons = event.currentTarget.querySelectorAll<HTMLButtonElement>("button");
        const first = buttons[0];
        const last = buttons[buttons.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }}
    >
      <motion.section
        initial={{ opacity: 0, scale: 0.96, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 12 }}
        className="relative max-h-full w-full max-w-sm overflow-y-auto rounded-md border border-slate-100 bg-white p-6 shadow-2xl shadow-slate-950/20"
      >
        <div className="absolute inset-x-0 top-0 h-1 bg-primary-500" />
        <button
          ref={closeButtonRef}
          type="button"
          onClick={onClose}
          aria-label="关闭社团分享二维码"
          className="absolute right-4 top-4 rounded-md p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/30"
        >
          <X size={18} />
        </button>
        <div className="pr-10">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-600">
            Share club
          </p>
          <h2 id="club-share-title" className="mt-1 font-display text-2xl font-bold text-slate-900">
            分享 {clubName}
          </h2>
          <p id="club-share-description" className="mt-2 text-sm leading-6 text-slate-500">
            扫码查看社团详情，了解近期活动。
          </p>
        </div>

        <div className="mt-6 flex justify-center rounded-md border border-slate-100 bg-slate-50 p-5">
          <div className="rounded-md bg-white p-3 shadow-sm">
            <QRCodeSVG
              ref={qrCodeRef}
              value={shareUrl}
              size={208}
              level="M"
              includeMargin={false}
              fgColor="#0f172a"
              bgColor="#ffffff"
              title={`${clubName} 社团分享二维码`}
            />
          </div>
        </div>

        <div className="mt-5 rounded-md border border-slate-100 bg-slate-50 p-3">
          <p className="truncate text-xs text-slate-500" title={shareUrl}>
            {shareUrl}
          </p>
        </div>
        {copyError && (
          <div className="mt-4" role="alert">
            <StatusMessage value={copyError} />
          </div>
        )}
        <div className="mt-4 grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={copyShareLink}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 active:scale-[0.98]"
          >
            {isLinkCopied ? <Check size={17} /> : <Share3 size={17} />}
            {isLinkCopied ? "已复制" : "复制链接"}
          </button>
          <button
            type="button"
            onClick={downloadQrCode}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary-500 px-4 py-3 text-sm font-semibold text-white shadow-md shadow-primary-500/20 transition hover:bg-primary-600 active:scale-[0.98]"
          >
            <QrCode size={17} /> 下载二维码
          </button>
        </div>
      </motion.section>
    </dialog>
  );
}
