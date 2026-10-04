import { useEffect, useState, type MouseEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type ProductDetail } from '../api'
import { askDan } from '../askDan'
import Swatches from '../components/Swatches'
import { useChatResults } from '../useChatResults'
import { stockIn, useMySize } from '../useMySize'

const LOW_STOCK = 5

function stockLabel(quantity: number) {
  if (quantity === 0) return 'Sold out'
  if (quantity <= LOW_STOCK) return `Only ${quantity} left`
  return `${quantity} in stock`
}

type Result = { id: string; status: 'ready' | 'missing' | 'error'; product?: ProductDetail }

export default function ProductPage() {
  const { productId = '' } = useParams()
  const [result, setResult] = useState<Result | null>(null)
  const { results: chatResults } = useChatResults()
  const { mySize, setMySize } = useMySize()

  useEffect(() => {
    fetchProduct(productId)
      .then((product) => setResult({ id: productId, status: 'ready', product }))
      .catch((e: Error) => setResult({ id: productId, status: e.message.startsWith('404') ? 'missing' : 'error' }))
  }, [productId])

  // Until the answer for *this* product arrives, show loading (not the last item viewed).
  if (!result || result.id !== productId) {
    return (
      <section className="section container">
        <div className="detail">
          <div className="card-skeleton detail-skeleton" />
          <div className="card-skeleton detail-skeleton" />
        </div>
      </section>
    )
  }
  const { status, product } = result
  if (status !== 'ready' || !product) {
    return (
      <section className="section container">
        <h1>{status === 'missing' ? "We couldn't find that item" : 'Something went wrong'}</h1>
        <p>
          {status === 'missing'
            ? "It may have moved, or the link may be off by a letter."
            : "We couldn't load this item right now. Please try again in a moment."}
        </p>
        <Link to="/products" className="btn">Back to all products</Link>
      </section>
    )
  }

  const sizesInStock = product.inventory.filter((s) => s.quantity > 0).length
  const myQty = stockIn(product.inventory, mySize)

  const askAssistant = askDan

  // Zoom follows the pointer, so shoppers can read lettering and see texture.
  function zoomTo(e: MouseEvent<HTMLDivElement>) {
    const box = e.currentTarget.getBoundingClientRect()
    e.currentTarget.style.setProperty('--zx', `${((e.clientX - box.left) / box.width) * 100}%`)
    e.currentTarget.style.setProperty('--zy', `${((e.clientY - box.top) / box.height) * 100}%`)
  }

  return (
    <section className="section container">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <span aria-hidden="true">/</span>
        <Link to="/products">{chatResults ? `Your chat results: ${chatResults.title}` : 'Products'}</Link>
        {!chatResults && (
          <>
            <span aria-hidden="true">/</span>
            <Link to={`/products?category=${encodeURIComponent(product.category)}`}>{product.category}</Link>
          </>
        )}
        <span aria-hidden="true">/</span>
        <span aria-current="page">{product.name}</span>
      </nav>
      <div className="detail">
        <div className="detail-image" onMouseMove={zoomTo}>
          <img src={product.image_url} alt={product.name} />
          <span className="zoom-hint">Hover to zoom</span>
        </div>

        <div className="detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          {mySize && myQty !== null && (
            <div className={`my-size-callout ${myQty === 0 ? 'sold-out' : ''}`}>
              <span>
                <strong>Your size {mySize}:</strong> {myQty === 0 ? 'sold out right now.' : `${stockLabel(myQty).toLowerCase()}.`}
              </span>
              {myQty === 0 && (
                <button className="btn btn-small" onClick={() => askAssistant(`This is sold out in my size. Can you find something similar in ${mySize}?`)}>
                  Find something similar in {mySize}
                </button>
              )}
            </div>
          )}
          <p className="detail-desc">{product.description}</p>
          <button className="btn btn-outline ask-dan-btn" onClick={() => askAssistant('Tell me about this one. Who is it a good fit for?')}>
            Ask Professor Dan about this
          </button>

          <h2 className="detail-heading">Colors</h2>
          <Swatches colors={product.colors} labels />

          <h2 className="detail-heading">Sizes and stock</h2>
          {product.inventory.length === 0 ? (
            <p className="muted">We don't have size information for this item yet.</p>
          ) : (
            <>
              <p className="muted">
                {sizesInStock === 0
                  ? 'Sold out in every size right now.'
                  : `Available in ${sizesInStock} of ${product.inventory.length} sizes.`}
              </p>
              <ul className="size-grid">
                {product.inventory.map((s) => (
                  <li key={s.size}>
                    <button
                      className={`size ${s.quantity === 0 ? 'size-out' : ''} ${mySize === s.size ? 'size-mine' : ''}`}
                      onClick={() => setMySize(mySize === s.size ? null : s.size)}
                      aria-pressed={mySize === s.size}
                      title={mySize === s.size ? 'Your size (tap to clear)' : 'Tap to set as your size'}
                    >
                      <span className="size-name">{s.size}</span>
                      <span className="size-stock">{stockLabel(s.quantity)}</span>
                      {mySize === s.size && <span className="size-tag">Your size</span>}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="hint">{mySize ? 'Tap another size to change your size.' : 'Tap a size to save it as your size. We will remember it across the shop.'}</p>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
