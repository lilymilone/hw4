import { useState, type ReactNode } from 'react'
import { SIZES } from './api'
import { MySizeContext } from './useMySize'

const KEY = 'cc-my-size'

function saved(): string | null {
  try {
    const s = localStorage.getItem(KEY)
    return s && SIZES.includes(s) ? s : null
  } catch {
    return null
  }
}

export function MySizeProvider({ children }: { children: ReactNode }) {
  const [mySize, setSize] = useState<string | null>(saved)

  function setMySize(size: string | null) {
    setSize(size)
    try {
      if (size) localStorage.setItem(KEY, size)
      else localStorage.removeItem(KEY)
    } catch {
      // private browsing: it still works for this visit
    }
  }

  return <MySizeContext.Provider value={{ mySize, setMySize }}>{children}</MySizeContext.Provider>
}
