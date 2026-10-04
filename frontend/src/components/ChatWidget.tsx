import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import {
  fetchChatHistory,
  fetchProduct,
  formatPrice,
  sendChatMessage,
  type PageContext,
  type PageResults,
  type ProductMatch,
} from '../api'
import { useAuth } from '../useAuth'
import { useChatResults } from '../useChatResults'
import ProfessorDan from './ProfessorDan'
import { useMySize } from '../useMySize'

type Message = {
  role: 'user' | 'assistant'
  text: string
  products?: ProductMatch[]
  page?: PageResults | null
  error?: boolean
  removed?: string[] // set on a shopper message the sensitive-info shield cleaned
}

const SMALL_SCREEN = 800 // px; below this the open chat would cover the results

// App.tsx gives this component key={user id}, so logging in or out starts a fresh
// widget: one shopper's chat never shows up for the next person on the same browser.
export default function ChatWidget() {
  const { user } = useAuth()
  const { showResults } = useChatResults()
  const { mySize } = useMySize()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [searchParams] = useSearchParams()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [savedCount, setSavedCount] = useState(0) // how many messages came from the saved chat
  const [draft, setDraft] = useState('')
  const [waiting, setWaiting] = useState(false)
  const [viewing, setViewing] = useState<{ id: string; name: string } | null>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Page context: what the shopper is looking at right now.
  const productId = pathname.match(/^\/products\/([^/]+)$/)?.[1] ?? null
  const pageContext: PageContext = {
    path: pathname,
    product_id: productId,
    category: searchParams.get('category'),
    my_size: mySize,
  }

  // Other parts of the site ("Ask Professor Dan", "Find something similar") open the
  // chat with a question already typed in.
  useEffect(() => {
    function onAsk(e: Event) {
      setDraft((e as CustomEvent<string>).detail)
      setOpen(true)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
    window.addEventListener('cc-ask-assistant', onAsk)
    return () => window.removeEventListener('cc-ask-assistant', onAsk)
  }, [])

  // Logged in: reload the saved chat from the database.
  useEffect(() => {
    if (!user) return
    fetchChatHistory()
      .then(({ messages: saved }) => {
        setMessages(saved.map((m) => ({ role: m.role, text: m.content, products: m.products })))
        setSavedCount(saved.length)
      })
      .catch(() => {})
  }, [user])

  // On a product page, show which item "this" means.
  useEffect(() => {
    if (!productId) return
    fetchProduct(productId)
      .then((p) => setViewing({ id: p.product_id, name: p.name }))
      .catch(() => setViewing(null))
  }, [productId])
  const viewingName = productId && viewing?.id === productId ? viewing.name : null

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages, waiting, open])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const greeting = user
    ? `${savedCount > 0 ? 'Ah, welcome back' : 'Ah, hello'}, ${user.first_name}! Professor Dan here, Campus Customs' resident bulldog scholar. Ask me about a style, a color, a size or a price, and I'll check our shop records for you.`
    : "Ah, hello there! I'm Professor Dan, Campus Customs' resident bulldog scholar. Ask me about a style, a color, a size or a price, and I'll check our shop records for you."

  async function handleSend(e: FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text || waiting) return
    // Guests: earlier turns go along so the assistant can follow the conversation.
    const history = messages.filter((m) => !m.error).map((m) => ({ role: m.role, content: m.text }))
    setDraft('')
    setMessages((m) => [...m, { role: 'user', text }])
    setWaiting(true)
    try {
      const { reply, products, page, removed, message_shown } = await sendChatMessage(text, history, pageContext)
      setMessages((m) => {
        const next = [...m]
        // The shield removed something: show the shopper exactly what was sent on and saved.
        if (removed.length && message_shown) next[next.length - 1] = { role: 'user', text: message_shown, removed }
        return [...next, { role: 'assistant', text: reply, products, page }]
      })
      if (page) putOnPage(page)
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', text: (err as Error).message, error: true }])
    } finally {
      setWaiting(false)
    }
  }

  // The API contract: `page` holds every match. Show them as cards on the Products page.
  function putOnPage(page: PageResults) {
    showResults(page)
    if (pathname !== '/products') navigate('/products')
    if (window.innerWidth < SMALL_SCREEN) setOpen(false)
  }

  function renderMessage(m: Message, i: number) {
    const bubble = <p className={`bubble bubble-${m.role} ${m.error ? 'bubble-error' : ''}`}>{m.text}</p>
    return (
      <div key={i} className={`turn turn-${m.role}`}>
        {m.role === 'assistant' ? (
          <div className="turn-row">
            <ProfessorDan size={30} className="dan-mini" />
            {bubble}
          </div>
        ) : (
          bubble
        )}
        {m.removed && m.removed.length > 0 && (
          <p className="shield-note" role="status">
            Removed for your safety: {m.removed.join(' and ')}. It wasn't saved or sent to our assistant.
          </p>
        )}
        {m.page && (
          <button className="chat-page-note" onClick={() => putOnPage(m.page!)}>
            Showing {m.page.total} {m.page.total === 1 ? 'item' : 'items'} on the page: {m.page.title} →
          </button>
        )}
        {m.products && m.products.length > 0 && (
          <ul className="chat-cards">
            {m.products.map((p) => (
              <li key={p.product_id}>
                <Link to={`/products/${p.product_id}`} className="chat-card">
                  <img src={p.image_url} alt="" />
                  <span className="chat-card-name">{p.name}</span>
                  <span className="chat-card-price">
                    {formatPrice(p.price)}
                    {!p.in_stock && ' · Sold out'}
                  </span>
                  {p.size && p.size_quantity !== null && (
                    <span className={`chat-card-size ${p.size_quantity === 0 ? 'sold-out' : ''}`}>
                      Size {p.size}: {p.size_quantity === 0 ? 'Sold out' : `${p.size_quantity} in stock`}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    )
  }

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Chat with Professor Dan">
          <header className="chat-header">
            <ProfessorDan size={50} mood={waiting ? 'thinking' : 'idle'} />
            <div className="chat-heading">
              <p className="chat-title">Professor Dan</p>
              <p className="chat-role">Resident bulldog scholar · Campus Customs</p>
              <p className="chat-subtitle">
                {user ? `Chatting as ${user.first_name} · saved to your account` : 'Guest chat · log in to save it'}
              </p>
            </div>
            <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
              ×
            </button>
          </header>

          <div className="chat-body">
            {/* The blue sunrise behind the conversation. */}
            <div className="chat-sky" aria-hidden="true">
              <span className="chat-sun" />
              <span className="chat-cloud chat-cloud-1" />
              <span className="chat-cloud chat-cloud-2" />
            </div>
            <div className="chat-messages" ref={listRef} aria-live="polite">
              {messages.slice(0, savedCount).map(renderMessage)}
              {savedCount > 0 && <p className="chat-divider">Your saved chat is above · picking up where you left off</p>}
              <div className="turn turn-assistant">
                <div className="turn-row">
                  <ProfessorDan size={30} className="dan-mini" mood="happy" />
                  <p className="bubble bubble-assistant">{greeting}</p>
                </div>
              </div>
              {messages.slice(savedCount).map((m, i) => renderMessage(m, savedCount + i))}
              {waiting && (
                <div className="turn turn-assistant">
                  <div className="turn-row">
                    <ProfessorDan size={30} className="dan-mini" mood="thinking" />
                    <p className="bubble bubble-assistant bubble-typing">
                      Professor Dan is consulting his notes
                      <span className="typing-dots" aria-hidden="true">
                        <i />
                        <i />
                        <i />
                      </span>
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {viewingName && (
            <p className="chat-context">
              Asking about <strong>{viewingName}</strong>. Try "Do you have this in pink?"
            </p>
          )}
          <form className="chat-form" onSubmit={handleSend}>
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={viewingName ? 'Ask about this item…' : 'Ask about a hoodie, a size, a price…'}
              aria-label="Your message"
              maxLength={1000}
            />
            <button type="submit" className="btn" disabled={!draft.trim() || waiting}>
              Send
            </button>
          </form>
        </section>
      )}

      <button
        className={`chat-launcher ${open ? 'is-open' : ''}`}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? 'Close chat' : 'Chat with Professor Dan'}
      >
        {open ? (
          <span className="launcher-close">×</span>
        ) : (
          <>
            <span className="launcher-face">
              <ProfessorDan size={46} />
            </span>
            <span className="launcher-label">Ask Professor Dan</span>
          </>
        )}
      </button>
    </div>
  )
}
