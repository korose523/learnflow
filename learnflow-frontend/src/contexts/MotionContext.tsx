import React, { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';

const STORAGE_KEY = 'lf_reduced_motion';

interface MotionContextValue {
  /** 是否应减弱动效（系统偏好 || 用户手动开关） */
  reduced: boolean;
  /** 用户手动开关（覆盖系统默认值） */
  manualReduced: boolean;
  setManualReduced: (v: boolean) => void;
  toggle: () => void;
}

const MotionContext = createContext<MotionContextValue | undefined>(undefined);

function getSystemPref(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function MotionProvider({ children }: { children: ReactNode }) {
  const [manualReduced, setManualReducedState] = useState<boolean>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === '1' ? true : stored === '0' ? false : getSystemPref();
  });
  const [systemReduced, setSystemReduced] = useState<boolean>(getSystemPref());

  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e: MediaQueryListEvent) => setSystemReduced(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const setManualReduced = useCallback((v: boolean) => {
    setManualReducedState(v);
    localStorage.setItem(STORAGE_KEY, v ? '1' : '0');
  }, []);

  const toggle = useCallback(() => {
    setManualReducedState(prev => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, next ? '1' : '0');
      return next;
    });
  }, []);

  // 减弱 = 手动开启 或 系统偏好
  const reduced = manualReduced || systemReduced;

  return (
    <MotionContext.Provider value={{ reduced, manualReduced, setManualReduced, toggle }}>
      {children}
    </MotionContext.Provider>
  );
}

export function useMotionPref(): MotionContextValue {
  const ctx = useContext(MotionContext);
  if (!ctx) throw new Error('useMotionPref must be used within MotionProvider');
  return ctx;
}
