import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CATEGORIES, type ProductSummary } from '../api'
import ProductCard from '../components/ProductCard'
import SizePicker from '../components/SizePicker'
import { useChatResults } from '../useChatResults'
import { stockIn, useMySize } from '../useMySize'
import { useProducts } from '../useProducts'

const SORTS = {
  featured: 'Featured',
  'price-asc': 'Price: low to high',
  'price-desc': 'Price: high to low',
  name: 'Name: A to Z',
} as const
type Sort = keyof typeof SORTS

// Every word the shopper types must appear somewhere in the product (name, description,
// colors, tags, shelf). "navy hockey" finds navy hockey items, not everything navy.
function matches(p: ProductSummary, words: string[]) {
  const text = [p.name, p.description, p.category, p.garment_type, ...p.colors, ...p.search_tags].join(' ').toLowerCase()
  return words.every((w) => text.includes(w) || (w.endsWith('s') && text.includes(w.slice(0, -1))))
}

// Opens the chat with a question typed in (ChatWidget listens for this).
function askAssistant(text: string) {
  window.dispatchEvent(new CustomEvent('cc-ask-assistant', { detail: text }))
}

export default function Products() {
  const { products, error } = useProducts()
  const { results, clearResults } = useChatResults()
  const { mySize } = useMySize()
  const [params, setParams] = useSearchParams()
  const searchRef = useRef<HTMLInputElement>(null)

  // Everything lives in the address bar, so a search can be shared or bookmarked.
  const category = params.get('category')
  const query = params.get('q') ?? ''
  const sort = (params.get('sort') as Sort) in SORTS ? (params.get('sort') as Sort) : 'featured'
  const onlyMySize = params.get('fit') === '1' && !!mySize

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) {
      if (v) next.set(k, v)
      else next.delete(k)
    }
    setParams(next, { replace: true })
  }

  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  const shown = (products ?? [])
    .filter((p) => !category || p.category === category)
    .filter((p) => matches(p, words))
    .filter((p) => !onlyMySize || (stockIn(p.inventory, mySize) ?? 0) > 0)
  if (sort === 'price-asc') shown.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
  if (sort === 'price-desc') shown.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
  if (sort === 'name') shown.sort((a, b) => a.name.localeCompare(b.name))

  // New results from the chat: bring the top of the page into view.
  const resultsKey = results?.key
  useEffect(() => {
    if (resultsKey) window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [resultsKey])

  // Press "/" anywhere on the page to jump to the search box.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement
      if (e.key === '/' && !typing) {
        e.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  function choose(c: string | null) {
    clearResults()
    update({ category: c })
  }

  const chips = (
    <div className="chips" role="group" aria-label="Filter by style">
      <button className={`chip ${!results && !category ? 'active' : ''}`} onClick={() => choose(null)}>
        All
      </button>
      {CATEGORIES.map((c) => (
        <button key={c} className={`chip ${!results && category === c ? 'active' : ''}`} onClick={() => choose(c)}>
          {c}
        </button>
      ))}
    </div>
  )

  if (results) {
    return (
      <section className="section container">
        <div className="chat-results-banner" aria-live="polite">
          <div>
            <p className="eyebrow">From your chat with Professor Dan</p>
            <h1>{results.title}</h1>
            <p className="muted">
              {results.total} {results.total === 1 ? 'item matches' : 'items match'}. Tap any one to see its
              sizes, stock and full details.
            </p>
          </div>
          <button className="btn btn-outline" onClick={() => choose(null)}>
            Show all products
          </button>
        </div>

        {chips}
        <SizePicker />

        <div className="product-grid" key={results.key}>
          {results.products.map((p, i) => (
            <ProductCard key={p.product_id} product={p} index={i} />
          ))}
        </div>
      </section>
    )
  }

  return (
    <section className="section container">
      <h1>{category ?? 'All products'}</h1>
      <p className="muted">
        Tap any item to see its sizes, stock and full details. Or ask Professor Dan, and the
        matches will show up right here.
      </p>

      {chips}

      <div className="toolbar">
        <div className="search">
          <input
            ref={searchRef}
            type="search"
            value={query}
            onChange={(e) => update({ q: e.target.value || null })}
            placeholder='Search: "hockey", "Saybrook", "navy crewneck"…  (press / )'
            aria-label="Search products"
          />
          {query && (
            <button className="search-clear" onClick={() => update({ q: null })} aria-label="Clear search">
              ×
            </button>
          )}
        </div>
        <label className="sort">
          Sort
          <select value={sort} onChange={(e) => update({ sort: e.target.value === 'featured' ? null : e.target.value })}>
            {Object.entries(SORTS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="toolbar toolbar-size">
        <SizePicker />
        <label className={`fit-toggle ${mySize ? '' : 'disabled'}`}>
          <input
            type="checkbox"
            checked={onlyMySize}
            disabled={!mySize}
            onChange={(e) => update({ fit: e.target.checked ? '1' : null })}
          />
          Only show items in stock in my size
        </label>
      </div>

      {error && <p className="notice">We couldn't load products right now. Please try again in a moment.</p>}
      {!products && !error && <p className="muted">Loading products…</p>}
      {products && (
        <p className="result-count">
          {shown.length === products.length ? `${shown.length} items` : `${shown.length} of ${products.length} items`}
          {query && <> matching “{query}”</>}
          {onlyMySize && <> in stock in size {mySize}</>}
        </p>
      )}

      {products && shown.length === 0 && (
        <div className="empty">
          <p>
            Nothing here matches{query ? <> “{query}”</> : ' those filters'}
            {onlyMySize ? ` in size ${mySize}` : ''}. Professor Dan can suggest something close.
          </p>
          <button
            className="btn"
            onClick={() =>
              askAssistant(
                query
                  ? `Do you have anything like "${query}"${onlyMySize ? ` in size ${mySize}` : ''}?`
                  : `What do you have${category ? ` in ${category.toLowerCase()}` : ''}${onlyMySize ? ` in size ${mySize}` : ''}?`,
              )
            }
          >
            Ask Professor Dan
          </button>
        </div>
      )}

      <div className="product-grid">
        {shown.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </section>
  )
}
