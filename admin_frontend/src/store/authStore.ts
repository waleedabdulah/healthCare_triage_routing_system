import { create } from 'zustand'
import axios from 'axios'

export interface AuthUser {
  id: string
  email: string
  fullName: string
  department: string | null
  role: 'nurse' | 'admin'
}

interface AuthState {
  user: AuthUser | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isAdmin: () => boolean
  isAuthenticated: () => boolean
  loadFromStorage: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,

  loadFromStorage: () => {
    try {
      const token = localStorage.getItem('admin_token')
      const userStr = localStorage.getItem('admin_user')
      if (token && userStr) {
        set({ token, user: JSON.parse(userStr) })
      }
    } catch {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_user')
    }
  },

  login: async (email: string, password: string) => {
    const res = await axios.post('/api/v1/auth/login', { email, password })
    const { access_token, user } = res.data
    const authUser: AuthUser = {
      id: user.id,
      email: user.email,
      fullName: user.full_name,
      department: user.department,
      role: user.role,
    }
    localStorage.setItem('admin_token', access_token)
    localStorage.setItem('admin_user', JSON.stringify(authUser))
    set({ token: access_token, user: authUser })
  },

  logout: () => {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_user')
    set({ token: null, user: null })
  },

  isAdmin: () => get().user?.role === 'admin',
  isAuthenticated: () => !!get().token,
}))
