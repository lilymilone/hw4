import { createContext, useContext } from 'react'
import type { createAccount, logIn, User } from './api'

export type Auth = {
  user: User | null
  checking: boolean
  logIn: typeof logIn
  createAccount: typeof createAccount
  logOut: () => Promise<void>
}

export const AuthContext = createContext<Auth | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
