import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

export function BrandShieldIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 64 64" fill="none" {...props}>
      <defs>
        <linearGradient id="brandShieldBg" x1="8" y1="8" x2="54" y2="58" gradientUnits="userSpaceOnUse">
          <stop stopColor="#0B58B6" />
          <stop offset="0.52" stopColor="#1B88E2" />
          <stop offset="1" stopColor="#0F5DC0" />
        </linearGradient>
        <linearGradient id="brandShieldRoad" x1="14" y1="36" x2="52" y2="44" gradientUnits="userSpaceOnUse">
          <stop stopColor="#0C58B4" />
          <stop offset="0.55" stopColor="#1EA5E7" />
          <stop offset="1" stopColor="#39C889" />
        </linearGradient>
      </defs>
      <path
        d="M32 4 55 13v18.6c0 14.3-8.8 23.7-23 28.4C17.8 55.3 9 45.9 9 31.6V13L32 4Z"
        fill="url(#brandShieldBg)"
      />
      <path
        d="M12.2 31.8c6.2-10 15.9-15.3 29.2-15.8 4.4-.1 8.8.2 13.1.8-4.4-1.8-9.4-2.8-14.8-2.8-13 0-23.8 4.4-31.2 13.2L12.2 31.8Z"
        fill="white"
      />
      <path
        d="M13 37.6c6.8 4.1 14.1 6.2 21.8 6.2 10.7 0 18.5-2.8 23.4-8.2-3.8 7.7-11.9 16-26.2 17.2-8 .6-14.9-1.3-20.7-5.5L13 37.6Z"
        fill="url(#brandShieldRoad)"
      />
      <path d="M20 25.2v7.6" stroke="white" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M29.5 22.6v11.2" stroke="white" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M39 22v10.2" stroke="white" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M48.5 24.1v6.5" stroke="white" strokeWidth="2.6" strokeLinecap="round" />
      <rect x="49.8" y="15.5" width="6.4" height="6.4" rx="1.2" fill="#2588E6" />
      <rect x="44" y="22.5" width="6.4" height="6.4" rx="1.2" fill="#35C77E" />
      <rect x="53.2" y="24.5" width="6.4" height="6.4" rx="1.2" fill="#2A82DF" />
      <rect x="48.1" y="31.2" width="6.4" height="6.4" rx="1.2" fill="#38D291" />
    </svg>
  );
}

export function DocsIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M7 4.75h7l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 6 19V6.25A1.5 1.5 0 0 1 7.5 4.75Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
      <path d="M14 4.75V9h4" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
      <path d="M9 12h6M9 15.5h6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  );
}

export function GuideIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M4.75 6.5A2.75 2.75 0 0 1 7.5 3.75H19.25v14.5H7.5A2.75 2.75 0 1 0 7.5 23.75H5.5a.75.75 0 0 1-.75-.75V6.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
      <path d="M8.5 7.5h7M8.5 11h7M8.5 14.5h4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  );
}

export function HelpIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.8"/>
      <path d="M9.6 9.2a2.48 2.48 0 1 1 4.62 1.24c-.56.8-1.72 1.3-1.72 2.56" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
      <circle cx="12" cy="16.8" r="1" fill="currentColor"/>
    </svg>
  );
}

export function SettingsIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M12 8.75A3.25 3.25 0 1 1 12 15.25A3.25 3.25 0 0 1 12 8.75Z" stroke="currentColor" strokeWidth="1.8"/>
      <path d="M4.75 13.2v-2.4l2-.62c.17-.5.38-.98.64-1.42l-.96-1.86 1.7-1.7 1.87.96c.44-.26.91-.47 1.41-.64l.62-2h2.4l.62 2c.5.17.97.38 1.41.64l1.87-.96 1.7 1.7-.96 1.86c.26.44.47.91.64 1.41l2 .63v2.4l-2 .62c-.17.5-.38.97-.64 1.41l.96 1.87-1.7 1.7-1.87-.96c-.44.26-.91.47-1.41.64l-.62 2h-2.4l-.62-2a7.3 7.3 0 0 1-1.41-.64l-1.87.96-1.7-1.7.96-1.87a7.3 7.3 0 0 1-.64-1.41l-2-.62Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  );
}

export function HomeIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="M4.75 10.1 12 4.75l7.25 5.35v8.15A1.75 1.75 0 0 1 17.5 20h-11a1.75 1.75 0 0 1-1.75-1.75V10.1Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path d="M9.75 20v-5.25h4.5V20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function EditIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d="m15.2 5.3 3.5 3.5m-2.1-4.9a2.15 2.15 0 0 1 3.05 3.05l-8.9 8.9-4.05 1 1-4.05 8.9-8.9Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M5.25 18.75H19" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function ChevronToggleIcon({ direction = "left", ...props }: IconProps & { direction?: "left" | "right" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path
        d={direction === "left" ? "m14.5 5-7 7 7 7" : "m9.5 5 7 7-7 7"}
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function FolderInputIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M3.75 7.25A2.5 2.5 0 0 1 6.25 4.75h4.2l1.5 1.75h5.8a2.5 2.5 0 0 1 2.5 2.5v7.75a2.5 2.5 0 0 1-2.5 2.5H6.25a2.5 2.5 0 0 1-2.5-2.5V7.25Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
      <path d="M12 10v6M9.25 13H12m0 0h2.75" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  );
}

export function FolderOutputIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M3.75 7.25A2.5 2.5 0 0 1 6.25 4.75h4.2l1.5 1.75h5.8a2.5 2.5 0 0 1 2.5 2.5v7.75a2.5 2.5 0 0 1-2.5 2.5H6.25a2.5 2.5 0 0 1-2.5-2.5V7.25Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
      <path d="M12 10v6M9.25 13H12m0 0h2.75" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" transform="rotate(180 12 13)"/>
    </svg>
  );
}

export function FileNodeIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path d="M7 4.75h7l4 4V19A1.5 1.5 0 0 1 16.5 20.5h-9A1.5 1.5 0 0 1 6 19V6.25A1.5 1.5 0 0 1 7.5 4.75Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/>
      <path d="M14 4.75V9h4" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/>
    </svg>
  );
}

export function SparkleIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" {...props}>
      <path d="m12 3 1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8L12 3Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
      <path d="m18.5 14 1 2.2 2.2 1-2.2 1-1 2.3-1-2.3-2.3-1 2.3-1 1-2.2ZM6 15.5l.8 1.7 1.7.8-1.7.8-.8 1.7-.8-1.7-1.7-.8 1.7-.8.8-1.7Z" fill="currentColor"/>
    </svg>
  );
}

export function FlagCN(props: IconProps) {
  return (
    <svg viewBox="0 0 64 44" fill="none" {...props}>
      <rect width="64" height="44" rx="8" fill="#DE2910" />
      <path d="m14.2 8 1.65 5.08h5.34l-4.32 3.13 1.65 5.08-4.32-3.14-4.32 3.14 1.65-5.08L7.2 13.08h5.34L14.2 8Z" fill="#FFDE00"/>
      <path d="m25.6 8.6 1 2.25 2.42.17-1.84 1.48.58 2.34-2.13-1.34-2.05 1.45.52-2.35-1.88-1.43 2.45-.11 0.93-2.26Z" fill="#FFDE00"/>
      <path d="m30.2 13.8.93 2.03 2.2.17-1.67 1.32.52 2.16-1.93-1.21-1.86 1.28.47-2.18-1.7-1.28 2.23-.12.81-2.17Z" fill="#FFDE00"/>
      <path d="m30 21.2.93 2.03 2.2.17-1.67 1.32.52 2.16-1.93-1.21-1.86 1.28.47-2.18-1.7-1.28 2.23-.12.81-2.17Z" fill="#FFDE00"/>
      <path d="m25 26.2 1 2.2 2.4.18-1.84 1.46.58 2.34L25 31.06l-2.05 1.46.52-2.36-1.88-1.42 2.45-.12L25 26.2Z" fill="#FFDE00"/>
    </svg>
  );
}

export function FlagEU(props: IconProps) {
  return (
    <svg viewBox="0 0 64 44" fill="none" {...props}>
      <rect width="64" height="44" rx="8" fill="#1E49A7" />
      {Array.from({ length: 12 }).map((_, idx) => {
        const angle = (idx / 12) * Math.PI * 2 - Math.PI / 2;
        const cx = 32 + Math.cos(angle) * 10.5;
        const cy = 22 + Math.sin(angle) * 10.5;
        return <circle key={idx} cx={cx} cy={cy} r="1.7" fill="#FFCC00" />;
      })}
    </svg>
  );
}

export function FlagUS(props: IconProps) {
  return (
    <svg viewBox="0 0 64 44" fill="none" {...props}>
      <rect width="64" height="44" rx="8" fill="#fff" />
      {Array.from({ length: 7 }).map((_, idx) => (
        <rect key={idx} x="0" y={idx * 6.28} width="64" height="3.14" fill="#B22234" />
      ))}
      <rect width="28" height="22" rx="8" fill="#3C3B6E" />
      {Array.from({ length: 3 }).flatMap((_, row) =>
        Array.from({ length: 4 }).map((__, col) => (
          <circle key={`${row}-${col}`} cx={5.5 + col * 5.2} cy={5.2 + row * 5.6} r="1" fill="white" />
        ))
      )}
    </svg>
  );
}
