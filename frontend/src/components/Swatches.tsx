// Color dots for a product's colors list, so shoppers see colors instead of reading them.
const COLOR_HEX: Record<string, string> = {
  navy: '#0b2a5b',
  'navy blue': '#0b2a5b',
  white: '#ffffff',
  ivory: '#fbf6e9',
  cream: '#f1e8d6',
  'heather gray': '#b9bcc2',
  gray: '#9aa0a6',
  'light gray': '#d3d6db',
  'charcoal gray': '#4a4d52',
  'heather charcoal gray': '#55585e',
  'dark heather gray': '#5f6368',
  'dark heather charcoal': '#4f5257',
  red: '#b3262e',
  blue: '#286dc0',
  'royal blue': '#2251b8',
  'light blue': '#9cc3ec',
  black: '#1b1b1b',
  yellow: '#f2c14e',
  gold: '#c9a227',
  green: '#2e7d4f',
  'dusty coral': '#d98a7b',
  multicolor: 'conic-gradient(#b3262e, #f2c14e, #2e7d4f, #286dc0, #b3262e)',
}

export default function Swatches({ colors, labels = false }: { colors: string[]; labels?: boolean }) {
  return (
    <ul className={`swatches ${labels ? 'swatches-labeled' : ''}`} aria-label={`Colors: ${colors.join(', ')}`}>
      {colors.map((c) => (
        <li key={c} title={c}>
          <span className="swatch" style={{ background: COLOR_HEX[c.toLowerCase()] ?? '#cfd4dc' }} />
          {labels && <span className="swatch-label">{c}</span>}
        </li>
      ))}
    </ul>
  )
}
