import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  apiClient,
  setAccessToken,
  getAccessToken,
  refreshAccessToken,
} from '../services/apiClient';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  default_workspace_id?: string;
}

export interface WorkspaceItem {
  id: string;
  name: string;
  owner_id: string;
  current_user_role: string;
  created_at: string;
}

interface AuthContextType {
  user: UserProfile | null;
  workspaces: WorkspaceItem[];
  currentWorkspace: WorkspaceItem | null;
  setCurrentWorkspace: (ws: WorkspaceItem) => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  forgotPassword: (email: string) => Promise<string>;
  resetPassword: (token: string, newPassword: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  refreshWorkspaces: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  const [currentWorkspace, setCurrentWorkspaceState] = useState<WorkspaceItem | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const setCurrentWorkspace = useCallback((ws: WorkspaceItem) => {
    setCurrentWorkspaceState(ws);
    try {
      localStorage.setItem('datalens_active_workspace_id', ws.id);
    } catch (e) {
      // ignore localStorage errors
    }
  }, []);

  const fetchProfile = useCallback(async () => {
    try {
      const resp = await apiClient<{ data: { user: UserProfile; workspaces: WorkspaceItem[] } }>('/api/v1/auth/me');
      const userData = resp.data.user;
      const wsList = resp.data.workspaces || [];

      setUser(userData);
      setWorkspaces(wsList);

      // Restore active workspace from localStorage or default
      const savedWsId = localStorage.getItem('datalens_active_workspace_id');
      const matched = wsList.find((w) => w.id === savedWsId);
      if (matched) {
        setCurrentWorkspaceState(matched);
      } else if (wsList.length > 0) {
        setCurrentWorkspaceState(wsList[0]);
      }
    } catch (err) {
      setUser(null);
      setWorkspaces([]);
      setCurrentWorkspaceState(null);
      setAccessToken(null);
    }
  }, []);

  // Hydrate session on browser refresh via silent token refresh
  useEffect(() => {
    let isMounted = true;

    async function initializeAuth() {
      try {
        const token = await refreshAccessToken();
        if (token && isMounted) {
          await fetchProfile();
        }
      } catch (e) {
        // Silent failure if offline or no active session
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    initializeAuth();

    return () => {
      isMounted = false;
    };
  }, [fetchProfile]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const resp = await apiClient<{ user: UserProfile; token: { access_token: string } }>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
        skipAuth: true,
      });

      setAccessToken(resp.token.access_token);
      setUser(resp.user);

      // Fetch workspaces list
      await fetchProfile();
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (fullName: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      const resp = await apiClient<{ user: UserProfile; token: { access_token: string } }>('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ full_name: fullName, email, password }),
        skipAuth: true,
      });

      setAccessToken(resp.token.access_token);
      setUser(resp.user);

      await fetchProfile();
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await apiClient('/api/v1/auth/logout', { method: 'POST' });
    } catch (e) {
      // Ignore network errors during logout
    } finally {
      setAccessToken(null);
      setUser(null);
      setWorkspaces([]);
      setCurrentWorkspaceState(null);
      localStorage.removeItem('datalens_active_workspace_id');
    }
  };

  const forgotPassword = async (email: string): Promise<string> => {
    const res = await apiClient<{ message: string }>('/api/v1/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
      skipAuth: true,
    });
    return res.message;
  };

  const resetPassword = async (token: string, newPassword: string) => {
    await apiClient('/api/v1/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
      skipAuth: true,
    });
  };

  const changePassword = async (currentPassword: string, newPassword: string) => {
    await apiClient('/api/v1/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    // Session invalidated on password change per security requirements
    setAccessToken(null);
    setUser(null);
    setWorkspaces([]);
    setCurrentWorkspaceState(null);
  };

  const refreshWorkspaces = async () => {
    if (!user) return;
    const resp = await apiClient<{ data: WorkspaceItem[] }>('/api/v1/workspaces');
    setWorkspaces(resp.data || []);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        workspaces,
        currentWorkspace,
        setCurrentWorkspace,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        forgotPassword,
        resetPassword,
        changePassword,
        refreshWorkspaces,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

