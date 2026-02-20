import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import { getApiUrl } from '../utils/api';

export interface User {
  email: string;
  name: string;
  onboarding_complete: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (credential: string) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Check if user is already authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await axios.get<User>(getApiUrl('/auth/me'));
        setUser(response.data);
      } catch (error) {
        // Not authenticated
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (credential: string): Promise<User> => {
    try {
      const response = await axios.post<User>(getApiUrl('/auth/google'), { credential });
      const userData = response.data;
      setUser(userData);
      return userData;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await axios.post(getApiUrl('/auth/logout'));
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
      throw error;
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
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
