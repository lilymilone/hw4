import { createContext, useContext } from 'react'
import type { PageResults } from './api'

// Search results the shop assistant put on the page. They stay put while the
// shopper opens a product and comes back, until they clear them or ask again.
// `key` changes with every new set, so the cards animate in fresh each time.
export type ShownResults = PageResults & { key: number }

export type ChatResults = {
  results: ShownResults | null
  showResults: (results: PageResults) => void
  clearResults: () => void
}

export const ChatResultsContext = createContext<ChatResults | null>(null)

export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
