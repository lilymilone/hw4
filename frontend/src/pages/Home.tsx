import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { CATEGORIES } from '../api'
import { askDan } from '../askDan'
import GarmentIcon from '../components/GarmentIcon'
import ProductCard from '../components/ProductCard'
import ProfessorDan from '../components/ProfessorDan'
import Skyline from '../components/Skyline'
import { useAuth } from '../useAuth'
import { useProducts } from '../useProducts'

// Each collection opens a chat with Professor Dan, who puts the matches on the page.
const COLLECTIONS = [
  {
    title: 'For the whole family',
    text: 'Mom, Dad, Grandpa, Aunt, Cousin and more. Pieces that let everyone show how proud they are of their Bulldog.',
    ask: 'Show me the Yale family pieces, like Mom, Dad and Grandpa.',
  },
  {
    title: 'Your residential college',
    text: 'Branford, Saybrook, Pierson, Grace Hopper and friends. Wear the college that feels like home.',
    ask: 'What do you have for the residential colleges?',
  },
  {
    title: 'Team spirit',
    text: 'Hockey, sailing, fencing, soccer, squash and many more. Cheer on the Bulldogs from the stands or the sofa.',
    ask: 'What Yale sports gear do you have?',
  },
  {
    title: 'Graduate and professional schools',
    text: 'Law, Medicine, Nursing, Management, Art, Music and more, for the next chapter of your Yale story.',
    ask: 'What do you have for the graduate and professional schools?',
  },
]

export default function Home() {
  const { products, error } = useProducts()
  const { user } = useAuth()

  // One product from each shelf, so the first look shows a little of everything.
  const featured = products
    ? CATEGORIES.map((c) => products.find((p) => p.category === c)).filter((p) => p !== undefined).slice(0, 4)
    : []

  return (
    <>
      <section className="hero">
        <div className="hero-stars" aria-hidden="true">
          {Array.from({ length: 14 }, (_, i) => (
            <span key={i} style={{ '--x': `${(i * 37) % 100}%`, '--y': `${(i * 23) % 45}%`, '--d': `${(i % 5) * 0.7}s` } as CSSProperties} />
          ))}
        </div>
        <div className="hero-sun" aria-hidden="true" />
        <div className="container hero-inner">
          <div className="hero-copy">
            <p className="eyebrow varsity">{user ? `Welcome back, ${user.first_name}` : '57 Broadway · New Haven'}</p>
            <h1>
              Yale blue,
              <br />
              <em>made for every day.</em>
            </h1>
            <p className="hero-text">
              Cozy hoodies, soft crewnecks and easy tees for students, families and anyone who loves New Haven.
              Find your favorite, pick your size, and let Professor Dan help along the way.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn btn-gold">
                Shop all products
              </Link>
              <button className="btn btn-outline-light" onClick={() => askDan('')}>
                Ask Professor Dan
              </button>
            </div>
          </div>
          <div className="hero-dan">
            <div className="pennant" aria-hidden="true">
              <span>Boola Boola</span>
            </div>
            <button className="speech" onClick={() => askDan('')}>
              Looking for something? <strong>Ask me!</strong>
            </button>
            <ProfessorDan size={190} mood="happy" />
          </div>
        </div>
        <Skyline className="hero-skyline" />
      </section>

      <section className="section container">
        <p className="eyebrow varsity section-kicker">Find your fit</p>
        <h2>Shop by style</h2>
        <div className="shelf-grid">
          {CATEGORIES.map((c) => (
            <Link key={c} to={`/products?category=${encodeURIComponent(c)}`} className="shelf">
              <GarmentIcon category={c} />
              <span>{c}</span>
              {products && <small>{products.filter((p) => p.category === c).length} items</small>}
            </Link>
          ))}
        </div>
      </section>

      <section className="section container">
        <div className="section-head">
          <div>
            <p className="eyebrow varsity section-kicker">Fresh off the rack</p>
            <h2>A few favorites to start</h2>
          </div>
          <Link to="/products" className="see-all">See everything →</Link>
        </div>
        {error && <p className="notice">We couldn't load products right now. Please try again in a moment.</p>}
        <div className="product-grid">
          {!products && !error && Array.from({ length: 4 }, (_, i) => <div key={i} className="card-skeleton" />)}
          {featured.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </section>

      <section className="section section-navy">
        <div className="container">
          <p className="eyebrow varsity section-kicker">Collections</p>
          <h2>Something for every Bulldog</h2>
          <div className="collection-grid">
            {COLLECTIONS.map((c, i) => (
              <button key={c.title} className="collection" onClick={() => askDan(c.ask)}>
                <span className="collection-num varsity">{String(i + 1).padStart(2, '0')}</span>
                <h3>{c.title}</h3>
                <p>{c.text}</p>
                <span className="collection-cta">Ask Professor Dan →</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="section container meet-dan">
        <ProfessorDan size={150} />
        <div>
          <p className="eyebrow varsity section-kicker">Office hours: always open</p>
          <h2>Meet Professor Dan</h2>
          <p>
            Our resident bulldog scholar knows every hoodie, crewneck and tee in the shop. Ask him about a style, a
            color, your size or a price. He checks our real shop records before he answers, and if he doesn't know
            something, he'll tell you so.
          </p>
          <button className="btn" onClick={() => askDan('')}>
            Start a chat
          </button>
        </div>
      </section>
    </>
  )
}
