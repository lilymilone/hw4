import { Link } from 'react-router-dom'

export default function About() {
  return (
    <>
      <section className="page-hero">
        <div className="container">
          <p className="eyebrow">About Us</p>
          <h1>A little shop with a lot of Bulldog pride.</h1>
        </div>
      </section>

      <section className="section container prose">
        <h2>Who we are</h2>
        <p>
          Campus Customs runs Yale Bulldog Blue, a shop for officially licensed Yale apparel. You'll find us at
          57 Broadway in New Haven, right by campus. We love this place, and we love helping people find
          something they'll be proud to wear.
        </p>

        <h2>What we carry</h2>
        <p>
          Hoodies, crewnecks, quarter-zips, tees and jackets, mostly in classic navy, white and gray. There are
          designs for every residential college, for Bulldog teams from hockey to sailing, for Yale's graduate
          and professional schools, and for the whole family, with pieces made for proud moms, dads,
          grandparents, aunts, uncles and cousins.
        </p>

        <h2>Who we're here for</h2>
        <p>
          First-years buying their first Yale sweatshirt. Seniors who want one more before they go. Families
          visiting for move-in or Commencement. Alumni coming back for The Game. Neighbors who just like the
          color blue. If Yale means something to you, you're welcome here.
        </p>

        <h2>Our promise</h2>
        <p>
          We'll always be honest with you. The prices and stock you see on this site come straight from our
          shop records, and our chat assistant uses those same records. If we don't know something, we'll
          say so instead of guessing.
        </p>

        <div className="about-cta">
          <Link to="/products" className="btn">Browse our products</Link>
          <Link to="/create-account" className="btn btn-outline">Create an account</Link>
        </div>
      </section>
    </>
  )
}
