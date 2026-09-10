import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { authApi } from '../services/api';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'student' | 'teacher' | 'parent' | 'admin';
  grade?: string;
  class_id?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string, role: string, grade?: string) => Promise<void>;
  oauthLogin: (provider: 'qq' | 'wechat', oauth_uid: string, name: string, role: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  const setToken = useCallback((data: any) => {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    localStorage.setItem('user_role', data.user?.role || data.role);
  }, []);

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setState(prev => ({ ...prev, isLoading: false }));
      return;
    }

    try {
      const response = await authApi.me();
      const userData = response.data ?? response;
      setState({
        user: userData,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch {
      // Token expired or invalid — try refresh
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const refreshResponse = await authApi.refresh?.(refreshToken);
          if (refreshResponse) {
            const data = refreshResponse.data ?? refreshResponse;
            setToken(data);
            // Retry loading user
            const meResponse = await authApi.me();
            const userData = meResponse.data ?? meResponse;
            setState({
              user: userData,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });
            return;
          }
        } catch { /* fall through to clear state */ }
      }

      // All attempts failed
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user_role');
      setState(prev => ({ ...prev, isLoading: false }));
    }
  }, [setToken]);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(async (email: string, password: string) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await authApi.login(email, password);
      const data = response.data ?? response;
      setToken(data);
      await loadUser();
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || '登录失败，请检查账号密码';
      setState(prev => ({ ...prev, isLoading: false, error: detail }));
      throw err;
    }
  }, [loadUser, setToken]);

  const register = useCallback(async (
    email: string, password: string, name: string, role: string, grade?: string
  ) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await authApi.register({ email, password, name, role, grade });
      const data = response.data ?? response;
      setToken(data);
      await loadUser();
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || '注册失败';
      setState(prev => ({ ...prev, isLoading: false, error: detail }));
      throw err;
    }
  }, [loadUser, setToken]);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_role');
    setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  }, []);

  const oauthLogin = useCallback(async (
    provider: 'qq' | 'wechat', oauth_uid: string, name: string, role: string
  ) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await authApi.oauthLogin({ provider, oauth_uid, name, role });
      const data = response.data ?? response;
      setToken(data);
      await loadUser();
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'OAuth 登录失败';
      setState(prev => ({ ...prev, isLoading: false, error: detail }));
      throw err;
    }
  }, [loadUser, setToken]);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, oauthLogin, logout, clearError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
