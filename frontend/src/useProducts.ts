import { useEffect, useState } from 'react'
import { fetchProducts, type ProductSummary } from './api'

export function useProducts() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError(true))
  }, [])

  return { products, error }
}
