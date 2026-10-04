import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../useAuth'
import { useChatResults } from '../useChatResults'

const TICKER = [
  'Officially licensed Yale apparel',
  '57 Broadway, New Haven',
  'Boola Boola!',
  'Ask Professor Dan about sizes and stock',
  'Hoodies · Crewnecks · Quarter-zips · Tees · Jackets',
  'For students, families and every Bulldog',
]

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const { user, checking, logOut } = useAuth()
  const { clearResults } = useChatResults()
  const navigate = useNavigate()

  async function handleLogOut() {
    await logOut()
    clearResults() // the last shopper's chat results shouldn't stay on the page
    navigate('/')
  }

  return (
    <header className="site-header">
      <div className="announce" aria-label="Officially licensed Yale apparel, 57 Broadway, New Haven">
        {/* A slow marquee; it pauses on hover and stands still for people who prefer less motion. */}
        <div className="ticker" aria-hidden="true">
          {[0, 1].map((copy) => (
            <span key={copy} className="ticker-run">
              {TICKER.map((t) => (
                <span key={t} className="ticker-item">
                  {t}
                </span>
              ))}
            </span>
          ))}
        </div>
      </div>
      <nav className="nav container" aria-label="Main">
        <Link to="/" className="wordmark" aria-label="Campus Customs home">
          <span className="wordmark-crest" aria-hidden="true">CC</span>
          <span className="wordmark-text">
            <span className="wordmark-name">Campus Customs</span>
            <span className="wordmark-sub">Yale Bulldog Blue</span>
          </span>
        </Link>

        <button
          className="nav-toggle"
          aria-expanded={open}
          aria-controls="nav-links"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? 'Close' : 'Menu'}
        </button>

        <ul id="nav-links" className={`nav-links ${open ? 'open' : ''}`} onClick={() => setOpen(false)}>
          {LINKS.map((l) => (
            <li key={l.to}>
              <NavLink to={l.to} end={l.end}>
                {l.label}
              </NavLink>
            </li>
          ))}
          {checking ? null : user ? (
            <>
              <li className="nav-greeting">Hi, {user.first_name}!</li>
              <li>
                <button className="btn btn-small btn-outline" onClick={handleLogOut}>
                  Log out
                </button>
              </li>
            </>
          ) : (
            <>
              <li>
                <NavLink to="/login">Log in</NavLink>
              </li>
              <li>
                <NavLink to="/create-account" className="btn btn-small">
                  Create Account
                </NavLink>
              </li>
            </>
          )}
        </ul>
      </nav>
    </header>
  )
}
