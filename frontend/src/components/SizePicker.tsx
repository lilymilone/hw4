import { SIZES } from '../api'
import { useMySize } from '../useMySize'

// The "My size" buttons. Choosing a size again clears it.
export default function SizePicker({ label = 'My size' }: { label?: string }) {
  const { mySize, setMySize } = useMySize()
  return (
    <div className="size-picker" role="group" aria-label={label}>
      <span className="size-picker-label">{label}:</span>
      {SIZES.map((s) => (
        <button
          key={s}
          className={`size-pill ${mySize === s ? 'active' : ''}`}
          aria-pressed={mySize === s}
          onClick={() => setMySize(mySize === s ? null : s)}
        >
          {s}
        </button>
      ))}
    </div>
  )
}
