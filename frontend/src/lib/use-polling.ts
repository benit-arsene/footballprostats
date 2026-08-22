"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { POLL_INTERVALS, shouldPoll } from "./api";

type UsePollingOptions<T> = {
  /** Async function that fetches the data */
  fetcher: () => Promise<T>;
  /** Polling interval in ms. Defaults to LIVE (15 s) */
  intervalMs?: number;
  /** When false, polling pauses (e.g. match not live) */
  enabled?: boolean;
  /** Called on each fetch error */
  onError?: (error: Error) => void;
};

/**
 * Generic polling hook.
 *
 * Repeatedly calls `fetcher` at `intervalMs` while `enabled` is true.
 * Stops automatically when the match status changes away from "live".
 *
 * Usage:
 *   const { data, error, isPolling } = usePolling({
 *     fetcher: () => getLiveMatches(),
 *     enabled: isLive,
 *   });
 */
export function usePolling<T>({
  fetcher,
  intervalMs = POLL_INTERVALS.LIVE,
  enabled = true,
  onError,
}: UsePollingOptions<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const start = useCallback(() => {
    stop();
    setIsPolling(true);

    const poll = async () => {
      try {
        const result = await fetcher();
        setData(result);
        setError(null);
      } catch (err) {
        const e = err instanceof Error ? err : new Error(String(err));
        setError(e);
        onError?.(e);
      }
    };

    // Immediate first fetch
    poll();
    intervalRef.current = setInterval(poll, intervalMs);
  }, [fetcher, intervalMs, onError, stop]);

  useEffect(() => {
    if (enabled) {
      start();
    } else {
      stop();
    }
    return stop;
  }, [enabled, start, stop]);

  return { data, error, isPolling };
}

/**
 * Convenience hook for a match-status-aware poller.
 * Automatically pauses polling when the match is not live.
 */
export function useMatchPolling<T>(
  fetcher: () => Promise<T>,
  status: string,
  intervalMs: number = POLL_INTERVALS.LIVE
) {
  return usePolling({
    fetcher,
    intervalMs,
    enabled: shouldPoll(status),
  });
}
