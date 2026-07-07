import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)

const API = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api' })

// Add token to all requests
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      API.get('/auth/me')
        .then((res) => setUser(res.data.user))
        .catch(() => { localStorage.removeItem('token'); setUser(null) })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email, password) => {
    const res = await API.post('/auth/login', { email, password })
    localStorage.setItem('token', res.data.token)
    setUser(res.data.user)
    return res.data
  }

  const signup = async (name, email, password) => {
    const res = await API.post('/auth/signup', { name, email, password })
    localStorage.setItem('token', res.data.token)
    setUser(res.data.user)
    return res.data
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  const updatePreferences = async (preferences) => {
    const res = await API.put('/user/preferences', preferences)
    const meRes = await API.get('/auth/me')
    setUser(meRes.data.user)
    return res.data
  }

  const updateProfile = async (data) => {
    const res = await API.put('/user/profile', data)
    const meRes = await API.get('/auth/me')
    setUser(meRes.data.user)
    return res.data
  }

  const updateAutoSearch = async (settings) => {
    const res = await API.put('/user/auto-search', settings)
    const meRes = await API.get('/auth/me')
    setUser(meRes.data.user)
    return res.data
  }

  const getAutoSearchStatus = async () => {
    const res = await API.get('/user/auto-search')
    return res.data.auto_search
  }

  const searchJobs = async () => {
    const res = await API.post('/jobs/search')
    return res.data
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, updatePreferences, updateProfile, updateAutoSearch, getAutoSearchStatus, searchJobs, API }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
