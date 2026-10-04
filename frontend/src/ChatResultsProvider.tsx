import { useState, type ReactNode } from 'react'
import type { PageResults } from './api'
import { ChatResultsContext, type ShownResults } from './useChatResults'

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ShownResults | null>(null)
  return (
    <ChatResultsContext.Provider
      value={{
        results,
        showResults: (r: PageResults) => setResults({ ...r, key: Date.now() }),
        clearResults: () => setResults(null),
      }}
    >
      {children}
    </ChatResultsContext.Provider>
  )
}
