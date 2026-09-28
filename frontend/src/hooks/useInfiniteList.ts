import { useCallback, useEffect, useRef, useState } from "react";

export const DEFAULT_PAGE_SIZE = 24;

export type PaginatedResult<T> = {
  items: T[];
  page: number;
  pages: number;
  total: number;
};

type PageResponse<T> = {
  data?: PaginatedResult<T>;
  error?: unknown;
  response?: Response;
};

export async function loadAllPages<T>(fetchPage: (page: number) => Promise<PageResponse<T>>) {
  const items: T[] = [];
  let page = 1;

  while (true) {
    const result = await fetchPage(page);
    if (result.error) {
      return { items: [], error: result.error, response: result.response };
    }

    items.push(...(result.data?.items || []));
    if (!result.data || page >= result.data.pages) {
      return { items, error: null, response: result.response };
    }
    page += 1;
  }
}

export function getPageResult<T>(
  data: PaginatedResult<T> | undefined,
  error: unknown,
  requestedPage: number,
): PaginatedResult<T> {
  if (error) throw error;
  return data || { items: [], page: requestedPage, pages: 0, total: 0 };
}

type PageLoader<T> = (page: number, signal: AbortSignal) => Promise<PaginatedResult<T>>;

export function useInfiniteList<T>(loadPage: PageLoader<T>, enabled = true) {
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const currentPageRef = useRef(0);
  const totalPagesRef = useRef(1);
  const isLoadingRef = useRef(false);
  const requestIdRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  const load = useCallback(
    async (reset: boolean): Promise<PaginatedResult<T> | undefined> => {
      if (isLoadingRef.current && !reset) return;

      if (reset) {
        abortControllerRef.current?.abort();
        currentPageRef.current = 0;
        totalPagesRef.current = 1;
        setItems([]);
        setTotal(0);
        setHasMore(false);
        setIsInitialLoading(true);
        setIsLoadingMore(false);
      } else {
        setIsLoadingMore(true);
      }

      isLoadingRef.current = true;
      setError(null);
      const requestedPage = reset ? 1 : currentPageRef.current + 1;
      const requestId = ++requestIdRef.current;
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const result = await loadPage(requestedPage, controller.signal);
        if (controller.signal.aborted || requestId !== requestIdRef.current) return;

        currentPageRef.current = result.page;
        totalPagesRef.current = result.pages;
        setItems((current) => (reset ? result.items : [...current, ...result.items]));
        setTotal(result.total);
        setHasMore(result.page < result.pages);
        return result;
      } catch (requestError) {
        if (controller.signal.aborted || requestId !== requestIdRef.current) return;
        setError(requestError);
      } finally {
        if (requestId === requestIdRef.current) {
          isLoadingRef.current = false;
          setIsInitialLoading(false);
          setIsLoadingMore(false);
        }
      }
    },
    [loadPage],
  );

  useEffect(() => {
    if (!enabled) {
      abortControllerRef.current?.abort();
      isLoadingRef.current = false;
      setIsInitialLoading(false);
      setIsLoadingMore(false);
      return;
    }
    void load(true);
    return () => {
      requestIdRef.current += 1;
      abortControllerRef.current?.abort();
      isLoadingRef.current = false;
    };
  }, [enabled, load]);

  const loadMore = useCallback(async () => {
    if (currentPageRef.current >= totalPagesRef.current) return;
    await load(false);
  }, [load]);

  const reload = useCallback(async () => {
    return load(true);
  }, [load]);

  return {
    items,
    total,
    hasMore,
    isInitialLoading,
    isLoadingMore,
    error,
    loadMore,
    reload,
  };
}
