import { useState, type CSSProperties } from 'react'

// Professor Dan: Handsome Dan the bulldog as a sweet, elderly professor.
// Drawn entirely in HTML/CSS (styles in index.css, "Professor Dan" section), so he
// can blink, tilt, think and react without any image files.
type Mood = 'idle' | 'thinking' | 'happy'

type Props = {
  size?: number // px; every part scales with it
  mood?: Mood
  className?: string
}

export default function ProfessorDan({ size = 64, mood = 'idle', className = '' }: Props) {
  const [wiggle, setWiggle] = useState(0) // tap him and he adjusts his glasses

  return (
    <div
      className={`dan dan-${mood} ${wiggle ? 'dan-poked' : ''} ${className}`}
      style={{ '--dan': `${size}px` } as CSSProperties}
      role="img"
      aria-label="Professor Dan, the Campus Customs bulldog"
      onClick={() => setWiggle((w) => w + 1)}
      onAnimationEnd={(e) => e.animationName === 'dan-poke' && setWiggle(0)}
    >
      <div className="dan-ear dan-ear-l" />
      <div className="dan-ear dan-ear-r" />
      <div className="dan-head">
        <div className="dan-patch" />
        <div className="dan-wrinkle" />
        <div className="dan-brow dan-brow-l" />
        <div className="dan-brow dan-brow-r" />
        <div className="dan-glasses">
          <span className="dan-lens">
            <i className="dan-eye" />
          </span>
          <span className="dan-lens">
            <i className="dan-eye" />
          </span>
        </div>
        <div className="dan-cheek dan-cheek-l" />
        <div className="dan-cheek dan-cheek-r" />
        <div className="dan-nose" />
        <div className="dan-mouth" />
        <div className="dan-tooth dan-tooth-l" />
        <div className="dan-tooth dan-tooth-r" />
      </div>
      <div className="dan-cap">
        <div className="dan-cap-top" />
        <div className="dan-cap-band" />
        <div className="dan-tassel" />
      </div>
      <div className="dan-bowtie">
        <span />
        <b />
        <span />
      </div>
    </div>
  )
}
