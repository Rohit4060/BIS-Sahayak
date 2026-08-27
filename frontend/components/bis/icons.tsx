import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

export function ChatIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <path d="M4 5.5h16v10H9.5L5 19v-3.5H4z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ShieldCheckIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <path d="M12 3.5 5 6v5.5c0 4.2 2.9 7.4 7 8.5 4.1-1.1 7-4.3 7-8.5V6l-7-2.5Z" strokeLinejoin="round" />
      <path d="m9 12 2 2 4-4.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function BookIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <path d="M4 5.5c2-1 5-1 7 0v13c-2-1-5-1-7 0v-13Z" strokeLinejoin="round" />
      <path d="M20 5.5c-2-1-5-1-7 0v13c2-1 5-1 7 0v-13Z" strokeLinejoin="round" />
    </svg>
  );
}

export function FlaskIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <path d="M10 3.5h4" strokeLinecap="round" />
      <path d="M10.5 3.5v6.2L5.8 17c-.9 1.5.2 3.3 1.9 3.3h8.6c1.7 0 2.8-1.8 1.9-3.3l-4.7-7.3V3.5" strokeLinejoin="round" />
      <path d="M8.3 15h7.4" strokeLinecap="round" />
    </svg>
  );
}

export function LinkIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <path d="M9.5 14.5 14.5 9.5" strokeLinecap="round" />
      <path d="M11 7.5 13 5.6a3.3 3.3 0 0 1 4.7 4.7L15.8 12" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M13 16.5 11 18.4a3.3 3.3 0 0 1-4.7-4.7L8.2 12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SearchIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="m19 19-4.3-4.3" strokeLinecap="round" />
    </svg>
  );
}

export function BadgeIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <circle cx="12" cy="9.5" r="5" />
      <path d="M9 13.8 8 21l4-2 4 2-1-7.2" strokeLinejoin="round" />
    </svg>
  );
}

export function MapPinIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <path d="M12 21s7-7.1 7-12a7 7 0 1 0-14 0c0 4.9 7 12 7 12Z" strokeLinejoin="round" />
      <circle cx="12" cy="9" r="2.4" />
    </svg>
  );
}

export function MenuIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <path d="M4 6.5h16M4 12h16M4 17.5h16" strokeLinecap="round" />
    </svg>
  );
}

export function CloseIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <path d="m5 5 14 14M19 5 5 19" strokeLinecap="round" />
    </svg>
  );
}

export function SendIcon({ className = "", ...props }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth={1.7} className={`stroke-current fill-none ${className}`} {...props}>
      <path d="M4 12 20 4l-6 16-2.5-7L4 12Z" strokeLinejoin="round" />
    </svg>
  );
}