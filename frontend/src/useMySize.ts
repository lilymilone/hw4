import { createContext, useContext } from 'react'

// "My size": the shopper picks their size once, and every card, the product page
// and the chat use it. Remembered in this browser (localStorage).
export type MySize = {
  mySize: string | null
  setMySize: (size: string | null) => void
}

export const MySizeContext = createContext<MySize | null>(null)

export function useMySize() {
  const ctx = useContext(MySizeContext)
  if (!ctx) throw new Error('useMySize must be used inside <MySizeProvider>')
  return ctx
}

// Stock for one size, or null if the product has no record for it.
export function stockIn(inventory: { size: string; quantity: number }[] | undefined, size: string | null) {
  if (!size || !inventory) return null
  return inventory.find((s) => s.size === size)?.quantity ?? null
}
