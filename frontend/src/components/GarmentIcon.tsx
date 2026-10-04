// Little line drawings for the five shelves, so "Shop by style" reads at a glance.
const PATHS: Record<string, string> = {
  Hoodies:
    'M24 14c0-5 4-9 8-9s8 4 8 9l12 6 6 16-8 3-3-7v30H17V32l-3 7-8-3 6-16zM26 14c1 6 3 9 6 9s5-3 6-9 M27 46h10v8H27z',
  Crewnecks: 'M24 9c2 4 5 6 8 6s6-2 8-6l12 5 6 22-8 3-4-12v35H18V27l-4 12-8-3 6-22zM26 10c2 3 4 4 6 4s4-1 6-4',
  'Quarter-zips': 'M24 9l8 4 8-4 12 5 6 22-8 3-4-12v35H18V27l-4 12-8-3 6-22zM32 13v16 M30 22h4',
  'Tees & tops': 'M23 9c2 4 5 6 9 6s7-2 9-6l13 6 5 13-9 4-3-6v36H17V26l-3 6-9-4 5-13zM25 10c2 3 4 4 7 4s5-1 7-4',
  Jackets: 'M24 9l8 6 8-6 12 5 6 24-8 2-4-12v34H18V28l-4 12-8-2 6-24zM32 15v47 M24 9l5 14-3 4 6 6 M40 9l-5 14 3 4-6 6',
}

export default function GarmentIcon({ category }: { category: string }) {
  return (
    <svg className="garment-icon" viewBox="0 0 64 64" aria-hidden="true">
      <path d={PATHS[category] ?? PATHS.Crewnecks} />
    </svg>
  )
}
