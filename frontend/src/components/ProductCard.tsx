import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice, SIZES, type SizeStock } from '../api'
import { stockIn, useMySize } from '../useMySize'

// Works for both the full catalogue (ProductSummary) and cards the chat put on
// the page (ProductMatch): both have these fields.
type CardProduct = {
  product_id: string
  name: string
  price: number
  image_url: string
  description: string
  category?: string
  size?: string | null
  size_quantity?: number | null
  inventory?: SizeStock[]
}

type Props = {
  product: CardProduct
  index?: number // set for chat results, so the cards fade in one after another
}

export default function ProductCard({ product, index }: Props) {
  const { mySize } = useMySize()
  const style = index === undefined ? undefined : ({ '--i': Math.min(index, 12) } as CSSProperties)
  // A size the shopper asked the chat about wins; otherwise their saved "My size".
  const asked = product.size && product.size_quantity !== null && product.size_quantity !== undefined
  const badgeSize = asked ? product.size : mySize
  const badgeQty = asked ? product.size_quantity! : stockIn(product.inventory, mySize)

  return (
    <Link
      to={`/products/${product.product_id}`}
      className={`card ${index === undefined ? '' : 'card-arrive'}`}
      style={style}
    >
      <div className="card-image">
        {product.category && <span className="card-stamp">{product.category}</span>}
        <img src={product.image_url} alt={product.name} loading="lazy" />
        <span className="price-tag">{formatPrice(product.price)}</span>
      </div>
      <div className="card-body">
        <h3 className="card-name">{product.name}</h3>
        {badgeSize && badgeQty !== null && (
          <p className={`card-size ${badgeQty === 0 ? 'sold-out' : ''}`}>
            {asked ? 'Size' : 'Your size'} {badgeSize}: {badgeQty === 0 ? 'Sold out' : `${badgeQty} in stock`}
          </p>
        )}
        <p className="card-desc">{product.description}</p>
        {product.inventory && product.inventory.length > 0 && (
          // Every size at a glance: crossed out = sold out, ringed = your size.
          <ul className="size-dots" aria-label="Sizes in stock">
            {SIZES.map((s) => {
              const q = stockIn(product.inventory, s)
              if (q === null) return null
              return (
                <li
                  key={s}
                  className={`${q === 0 ? 'out' : ''} ${s === mySize ? 'mine' : ''}`}
                  title={q === 0 ? `${s}: sold out` : `${s}: ${q} in stock`}
                >
                  {s}
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </Link>
  )
}
