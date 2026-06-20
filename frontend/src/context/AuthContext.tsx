import React, { createContext, useState, useEffect, useContext } from 'react';

interface User {
  id: number;
  username: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
  apiFetch: (url: string, options?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const getApiUrl = (path: string) => {
  const baseUrl = import.meta.env.VITE_API_URL || '';
  if (baseUrl) {
    return `${baseUrl.replace(/\/$/, '')}${path}`;
  }
  return path;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    // Check if token exists in localStorage on startup
    const storedToken = localStorage.getItem('talkbuddy_token');
    if (storedToken) {
      setToken(storedToken);
      try {
        // Decode JWT payload to get user details
        const payloadBase64 = storedToken.split('.')[1];
        const decodedPayload = JSON.parse(atob(payloadBase64));
        setUser({
          id: decodedPayload.id,
          username: decodedPayload.sub
        });
      } catch (err) {
        console.error('Error decoding token:', err);
        // Clear corrupt token
        localStorage.removeItem('talkbuddy_token');
      }
    }
    setLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const response = await fetch(getApiUrl('/api/auth/login'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Login failed');
    }

    const data = await response.json();
    const jwtToken = data.access_token;
    
    localStorage.setItem('talkbuddy_token', jwtToken);
    setToken(jwtToken);
    
    const payloadBase64 = jwtToken.split('.')[1];
    const decodedPayload = JSON.parse(atob(payloadBase64));
    setUser({
      id: decodedPayload.id,
      username: decodedPayload.sub
    });
  };

  const register = async (username: string, password: string) => {
    const response = await fetch(getApiUrl('/api/auth/register'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Registration failed');
    }
  };

  const logout = () => {
    localStorage.removeItem('talkbuddy_token');
    setToken(null);
    setUser(null);
  };

  // Helper fetch function that automatically appends the JWT bearer token
  const apiFetch = async (url: string, options: RequestInit = {}) => {
    const headers = new Headers(options.headers || {});
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    
    // Resolves path using getApiUrl to allow remote backend in production
    return fetch(getApiUrl(url), {
      ...options,
      headers
    });
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, apiFetch }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
