import { Link } from 'react-router-dom'
import ProfessorDan from '../components/ProfessorDan'

export default function NotFound() {
  return (
    <section className="section container not-found">
      <ProfessorDan size={170} mood="thinking" />
      <div>
        <p className="eyebrow varsity section-kicker">Page not found</p>
        <h1>This page wandered off to the library</h1>
        <p>Professor Dan looked in every stack and couldn't find it. Plenty of Yale blue is still right here, though.</p>
        <Link to="/" className="btn">Back to Home</Link>
      </div>
    </section>
  )
}
