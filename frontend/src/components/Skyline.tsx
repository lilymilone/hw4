// A Gothic campus skyline silhouette (towers, spires, gables, lit windows), drawn as
// inline SVG so it stays crisp at any width and takes its color from CSS.
export default function Skyline({ className = '' }: { className?: string }) {
  return (
    <svg className={`skyline ${className}`} viewBox="0 0 1200 170" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
      <g className="skyline-far">
        <path d="M0 170 V120 H60 V100 L80 84 L100 100 V120 H170 V108 H230 V96 L250 80 L270 96 V170 Z" />
        <path d="M820 170 V112 H880 V98 L905 78 L930 98 V112 H990 V104 H1060 V90 L1080 74 L1100 90 V120 H1200 V170 Z" />
      </g>
      <g className="skyline-near">
        {/* left halls with gables */}
        <path d="M0 170 V136 H40 V122 L70 104 L100 122 V136 H150 V126 L176 108 L202 126 V170 Z" />
        {/* the big clock tower */}
        <path d="M250 170 V70 H262 V44 H270 V30 H276 V10 L280 0 L284 10 V30 H290 V44 H298 V70 H310 V170 Z" />
        <path d="M244 72 L250 62 L256 72 Z M304 72 L310 62 L316 72 Z" />
        {/* chapel with a steep roof and a spire */}
        <path d="M330 170 V118 L380 88 L430 118 V170 Z M372 92 V60 L380 44 L388 60 V92 Z" />
        {/* long college range */}
        <path d="M440 170 V128 H480 V118 L500 106 L520 118 V128 H600 V118 L620 106 L640 118 V128 H700 V170 Z" />
        {/* library tower */}
        <path d="M700 170 V96 H714 V76 L740 52 L766 76 V96 H780 V170 Z" />
        <path d="M708 98 L714 88 L720 98 Z M760 98 L766 88 L772 98 Z" />
        {/* right halls */}
        <path d="M780 170 V132 H840 V120 L866 102 L892 120 V132 H960 V124 H1000 V110 L1020 98 L1040 110 V170 Z" />
        <path d="M1040 170 V100 H1052 V82 H1060 V70 L1066 58 L1072 70 V82 H1080 V100 H1092 V170 Z" />
        <path d="M1092 170 V134 H1150 V122 L1172 108 L1194 122 V134 H1200 V170 Z" />
      </g>
      <g className="skyline-windows">
        <rect x="273" y="52" width="4" height="8" rx="2" />
        <rect x="283" y="52" width="4" height="8" rx="2" />
        <circle cx="280" cy="38" r="4" />
        <rect x="376" y="128" width="8" height="16" rx="4" />
        <rect x="736" y="104" width="8" height="14" rx="4" />
        <rect x="490" y="140" width="5" height="9" rx="2" />
        <rect x="560" y="140" width="5" height="9" rx="2" />
        <rect x="630" y="140" width="5" height="9" rx="2" />
        <rect x="860" y="140" width="5" height="9" rx="2" />
        <rect x="1063" y="112" width="5" height="9" rx="2" />
        <rect x="60" y="144" width="5" height="9" rx="2" />
      </g>
    </svg>
  )
}
