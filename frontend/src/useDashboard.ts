import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchDashboard } from './api';
import type { DashboardData } from './types';

const REFRESH_MS = 60_000;

interface State {
  data: DashboardData | null;
  error: string | null;
  loading: boolean;
  updatedAt: Date | null;
}

export function useDashboard() {
  const [state, setState] = useState<State>({
    data: null,
    error: null,
    loading: true,
    updatedAt: null,
  });
  const inFlight = useRef<AbortController | null>(null);

  const load = useCallback(async (quiet = false) => {
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    if (!quiet) setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fetchDashboard(controller.signal);
      setState({ data, error: null, loading: false, updatedAt: new Date() });
    } catch (err) {
      if (controller.signal.aborted) return;
      setState((s) => ({
        ...s,
        loading: false,
        error: err instanceof Error ? err.message : 'Could not reach the Proof Ledger API',
      }));
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(true), REFRESH_MS);
    return () => {
      window.clearInterval(timer);
      inFlight.current?.abort();
    };
  }, [load]);

  return { ...state, refresh: () => void load() };
}
