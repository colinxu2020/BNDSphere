import { useEffect, useRef } from "react";

export function InfiniteScrollTrigger({
  hasMore,
  isLoading,
  error,
  onLoadMore,
}: {
  hasMore: boolean;
  isLoading: boolean;
  error?: unknown;
  onLoadMore: () => void | Promise<void>;
}) {
  const triggerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const trigger = triggerRef.current;
    if (!trigger || !hasMore || isLoading || error) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void onLoadMore();
      },
      { rootMargin: "320px 0px" },
    );
    observer.observe(trigger);
    return () => observer.disconnect();
  }, [error, hasMore, isLoading, onLoadMore]);

  if (!hasMore) return null;

  return (
    <div
      ref={triggerRef}
      className="flex min-h-14 items-center justify-center py-3 text-sm text-slate-500"
      role="status"
      aria-live="polite"
    >
      {isLoading ? (
        <span className="inline-flex items-center gap-2 font-medium">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-primary-500" />
          正在加载更多...
        </span>
      ) : (
        <button
          type="button"
          onClick={() => void onLoadMore()}
          className="rounded-md px-4 py-2 font-semibold text-primary-700 transition hover:bg-primary-50"
        >
          {error ? "加载失败，点击重试" : "加载更多"}
        </button>
      )}
    </div>
  );
}
