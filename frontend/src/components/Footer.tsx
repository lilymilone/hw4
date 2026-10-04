import { Link } from 'react-router-dom'
import ProfessorDan from './ProfessorDan'
import Skyline from './Skyline'

export default function Footer() {
  return (
    <footer className="site-footer">
      <Skyline className="footer-skyline" />
      <div className="container footer-grid">
        <div className="footer-sign">
          <ProfessorDan size={72} />
          <div>
            <p className="footer-brand">Campus Customs</p>
            <p>Yale apparel for students, families and fans.</p>
            <p className="footer-boola varsity">Boola Boola!</p>
          </div>
        </div>
        <div>
          <p className="footer-heading">Visit us</p>
          <p>
            57 Broadway
            <br />
            New Haven, CT 06511
          </p>
        </div>
        <div>
          <p className="footer-heading">Explore</p>
          <ul>
            <li><Link to="/products">Products</Link></li>
            <li><Link to="/about">About Us</Link></li>
            <li><Link to="/create-account">Create Account</Link></li>
          </ul>
        </div>
      </div>
      <p className="container footer-note">Prices and stock on this site come straight from our shop records.</p>
    </footer>
  )
}
