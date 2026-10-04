import { useEffect, useState, type ReactNode } from 'react'
import { createAccount, fetchMe, logIn, logOut, type User } from './api'
import { AuthContext, type Auth } from './useAuth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(true)

  // On page load, ask the backend whether this browser is already logged in.
  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false))
  }, [])

  const value: Auth = {
    user,
    checking,
    logIn: async (email, password) => {
      const u = await logIn(email, password)
      setUser(u)
      return u
    },
    createAccount: async (fields) => {
      const u = await createAccount(fields)
      setUser(u)
      return u
    },
    logOut: async () => {
      await logOut()
      setUser(null)
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
