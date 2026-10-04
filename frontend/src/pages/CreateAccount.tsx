import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../useAuth'

const MIN_PASSWORD = 8

export default function CreateAccount() {
  const { user, createAccount } = useAuth()
  const navigate = useNavigate()
  const [fields, setFields] = useState({ first_name: '', last_name: '', email: '', password: '' })
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user && !busy) return <Navigate to="/" replace />

  const set = (key: keyof typeof fields) => (e: ChangeEvent<HTMLInputElement>) =>
    setFields((f) => ({ ...f, [key]: e.target.value }))

  const mismatch = confirm.length > 0 && confirm !== fields.password

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (fields.password.length < MIN_PASSWORD) return setError(`Please choose a password with at least ${MIN_PASSWORD} characters.`)
    if (fields.password !== confirm) return setError("Those passwords don't match yet. Please try again.")
    setBusy(true)
    try {
      await createAccount(fields)
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  return (
    <section className="section container auth">
      <div className="auth-card">
        <h1>Create your account</h1>
        <p className="muted">It only takes a minute, and Professor Dan will know you by name.</p>

        <form onSubmit={handleSubmit} className="form">
          <div className="form-row">
            <label>
              First name
              <input autoComplete="given-name" value={fields.first_name} onChange={set('first_name')} maxLength={50} required />
            </label>
            <label>
              Last name
              <input autoComplete="family-name" value={fields.last_name} onChange={set('last_name')} maxLength={50} required />
            </label>
          </div>
          <label>
            Email
            <input type="email" autoComplete="email" value={fields.email} onChange={set('email')} required />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete="new-password"
              value={fields.password}
              onChange={set('password')}
              minLength={MIN_PASSWORD}
              maxLength={128}
              required
            />
            <small className="hint">At least {MIN_PASSWORD} characters.</small>
          </label>
          <label>
            Confirm password
            <input
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              aria-invalid={mismatch}
              required
            />
            {mismatch && <small className="hint hint-error">Passwords don't match yet.</small>}
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button type="submit" className="btn btn-block" disabled={busy}>
            {busy ? 'Creating your account…' : 'Create account'}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </section>
  )
}
