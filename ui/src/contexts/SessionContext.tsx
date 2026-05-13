import type { ReactNode } from 'react';
import { createContext, useContext, useState, useCallback, useRef } from 'react';

interface Alert {
  type: string;
  event: string;
  session_id: string;
  timestamp: number;
  duration?: number;
}

interface Stats {
  total_records: number;
  attentive_pct: number;
  distracted_pct: number;
  warning_pct: number;
  phone_events: number;
  gaze_outside_events: number;
  extra_person_events: number;
  mouth_covered_events: number;
  duration_seconds: number;
  current_state?: string;
}

interface SessionState {
  sessionId: string | null;
  isActive: boolean;
  frameSrc: string | null;
  stats: Stats;
  alerts: Alert[];
  settings: any;
  status: 'idle' | 'starting' | 'active' | 'stopping';
  error: string | null;
}

interface SessionContextType extends SessionState {
  startSession: () => Promise<void>;
  stopSession: () => Promise<void>;
  fetchSettings: () => Promise<void>;
  updateSettings: (data: any) => Promise<void>;
  clearAlerts: () => void;
  dismissError: () => void;
  addFrame: (src: string) => void;
  addStats: (stats: Stats) => void;
  addAlert: (alert: Alert) => void;
  setStatus: (status: SessionState['status']) => void;
  setError: (error: string | null) => void;
  setSessionId: (id: string | null) => void;
}

const defaultStats: Stats = {
  total_records: 0,
  attentive_pct: 0,
  distracted_pct: 0,
  warning_pct: 0,
  phone_events: 0,
  gaze_outside_events: 0,
  extra_person_events: 0,
  mouth_covered_events: 0,
  duration_seconds: 0,
};

const SessionContext = createContext<SessionContextType | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [frameSrc, setFrameSrc] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats>(defaultStats);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [settings, setSettings] = useState<any>({});
  const [status, setStatus] = useState<SessionState['status']>('idle');
  const [error, setError] = useState<string | null>(null);
  const statsRef = useRef<Stats>(defaultStats);

  const API_BASE = '';

  const startSession = useCallback(async () => {
    setStatus('starting');
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/session/start`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to start session');
      setSessionId(data.session_id);
      setIsActive(true);
      setStatus('active');
    } catch (e: any) {
      setError(e.message);
      setStatus('idle');
    }
  }, []);

  const stopSession = useCallback(async () => {
    setStatus('stopping');
    try {
      const res = await fetch(`${API_BASE}/api/v1/session/stop`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to stop session');
      setIsActive(false);
      setSessionId(null);
      setStatus('idle');
      setFrameSrc(null);
    } catch (e: any) {
      setError(e.message);
      setStatus('idle');
    }
  }, []);

  const fetchSettings = useCallback(async () => {
    const res = await fetch(`${API_BASE}/api/v1/settings`);
    const data = await res.json();
    setSettings(data);
  }, []);

  const updateSettings = useCallback(async (data: any) => {
    const res = await fetch(`${API_BASE}/api/v1/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const updated = await res.json();
    setSettings(updated);
  }, []);

  const clearAlerts = useCallback(() => setAlerts([]), []);
  const dismissError = useCallback(() => setError(null), []);

  const addFrame = useCallback((src: string) => setFrameSrc(src), []);

  const addStats = useCallback((newStats: Stats) => {
    statsRef.current = { ...statsRef.current, ...newStats };
    setStats({ ...statsRef.current });
  }, []);

  const addAlert = useCallback((alert: Alert) => {
    setAlerts(prev => [alert, ...prev].slice(0, 50));
  }, []);

  return (
    <SessionContext.Provider value={{
      sessionId, isActive, frameSrc, stats, alerts, settings, status, error,
      startSession, stopSession, fetchSettings, updateSettings,
      clearAlerts, dismissError, addFrame, addStats, addAlert, setStatus, setError, setSessionId,
    }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be inside SessionProvider');
  return ctx;
}
