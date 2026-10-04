// Everything the front end needs from the backend (backend/main.py).

export type SizeStock = { size: string; quantity: number }

export type ProductSummary = {
  product_id: string
  name: string
  garment_type: string
  category: string
  description: string
  colors: string[]
  price: number
  image_url: string
  total_stock: number
  search_tags: string[]
  inventory: SizeStock[] // stock in every size, for "My size" badges
}

export type ProductDetail = ProductSummary

export const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

// The order the shelves appear in on the Home and Products pages.
export const CATEGORIES = ['Hoodies', 'Crewnecks', 'Quarter-zips', 'Tees & tops', 'Jackets']

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const fetchProducts = () => getJson<ProductSummary[]>('/api/products')

export const fetchProduct = (productId: string) =>
  getJson<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)

// ---- Accounts (backend/auth.py). The login lives in an HttpOnly cookie that
// JavaScript can't read; these calls just send it along.

export type User = {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
}

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : 'Something went wrong. Please try again.'
    throw new Error(detail)
  }
  return data as T
}

export const fetchMe = () => getJson<User | null>('/api/auth/me')

export const logIn = (email: string, password: string) => postJson<User>('/api/auth/login', { email, password })

export const createAccount = (fields: { first_name: string; last_name: string; email: string; password: string }) =>
  postJson<User>('/api/auth/register', fields)

export const logOut = () => postJson<{ ok: boolean }>('/api/auth/logout')

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

// ---- Shop assistant chat (backend/main.py -> agent.py)

// One product card, in the chat or on the page. Every field comes from the database.
export type ProductMatch = {
  product_id: string // the card opens /products/{product_id}
  name: string
  price: number
  image_url: string
  description: string
  category: string
  in_stock: boolean
  size: string | null // set when the shopper asked about one size
  size_quantity: number | null
  inventory: SizeStock[] // stock in every size, for "My size" badges
}

// Search results the assistant asked to show on the Products page.
export type PageResults = {
  title: string
  total: number
  products: ProductMatch[]
}

export type ChatTurn = { role: 'user' | 'assistant'; content: string }

// The API contract for one chat message (backend/models.py ChatResponse).
export type ChatReply = {
  reply: string // shown in the chat panel
  products: ProductMatch[] // a few picks, as small cards under the reply
  page: PageResults | null // every match, as cards on the Products page (null = leave the page alone)
  removed: string[] // what the sensitive-info shield took out, e.g. ["a card number"]
  message_shown: string | null // the message as it was sent on and saved, when something was removed
}

// Where the shopper is when they send a message, so "do you have this in pink?"
// on a product page means that product. The backend checks it against the database.
export type PageContext = {
  path: string
  product_id: string | null // set on a single-item page
  category: string | null // set when a style chip is chosen on Products
  my_size: string | null // the size picked with "My size"
}

// Guests: the backend reads these last 20 turns for context. Logged in: the backend
// uses the saved conversation from the database instead.
const HISTORY_TURNS = 20

export const sendChatMessage = (message: string, history: ChatTurn[], page: PageContext) =>
  postJson<ChatReply>('/api/chat', { message, history: history.slice(-HISTORY_TURNS), page })

// A logged-in shopper's saved chat (guests get saved: false and no messages).
export type SavedMessage = { role: 'user' | 'assistant'; content: string; products: ProductMatch[]; created_at: string }
export type ChatHistory = { saved: boolean; messages: SavedMessage[] }

export const fetchChatHistory = () => getJson<ChatHistory>('/api/chat/history')
