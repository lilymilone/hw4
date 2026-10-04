import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.tsx'
import { AuthProvider } from './AuthProvider.tsx'
import { ChatResultsProvider } from './ChatResultsProvider.tsx'
import { MySizeProvider } from './MySizeProvider.tsx'
import '@fontsource/graduate'
import '@fontsource-variable/fraunces/full.css'
import '@fontsource-variable/inter'
import './index.css'
import './design.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ChatResultsProvider>
          <MySizeProvider>
            <App />
          </MySizeProvider>
        </ChatResultsProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
