import type { ReactNode, SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & {
  size?: number | string;
  strokeWidth?: number | string;
};

function SvgIcon({
  size = 24,
  strokeWidth = 2,
  className,
  children,
  ...props
}: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

function makeIcon(children: ReactNode) {
  return function Icon(props: IconProps) {
    return <SvgIcon {...props}>{children}</SvgIcon>;
  };
}

export const AlertCircle = makeIcon([
  <circle key="a" cx="12" cy="12" r="9" />,
  <path key="b" d="M12 7v6" />,
  <path key="c" d="M12 17h.01" />,
]);
export const ArrowLeft = makeIcon([
  <path key="a" d="M19 12H5" />,
  <path key="b" d="M11 6l-6 6 6 6" />,
]);
export const ArrowUpRight = makeIcon([
  <path key="a" d="M7 17 17 7" />,
  <path key="b" d="M9 7h8v8" />,
]);
export const Award = makeIcon([
  <circle key="a" cx="12" cy="8" r="4" />,
  <path key="b" d="M9 12 7 21l5-3 5 3-2-9" />,
]);
export const Bell = makeIcon([
  <path key="a" d="M6 10a6 6 0 0 1 12 0v4l2 3H4l2-3z" />,
  <path key="b" d="M10 20h4" />,
]);
export const Building2 = makeIcon([
  <path key="a" d="M5 21V4h10v17" />,
  <path key="b" d="M15 9h4v12" />,
  <path key="c" d="M8 8h4M8 12h4M8 16h4" />,
  <path key="d" d="M3 21h18" />,
]);
export const Calendar = makeIcon([
  <rect key="a" x="4" y="5" width="16" height="15" rx="2" />,
  <path key="b" d="M8 3v4M16 3v4M4 10h16" />,
]);
export const CalendarDays = Calendar;
export const Check = makeIcon([<path key="a" d="m5 12 5 5L20 7" />]);
export const CheckCircle2 = makeIcon([
  <circle key="a" cx="12" cy="12" r="9" />,
  <path key="b" d="m8 12 3 3 5-6" />,
]);
export const ChevronRight = makeIcon([<path key="a" d="m9 6 6 6-6 6" />]);
export const ClipboardList = makeIcon([
  <rect key="a" x="6" y="4" width="12" height="17" rx="2" />,
  <path key="b" d="M9 4h6M9 10h6M9 14h6M9 18h4" />,
]);
export const Clock = makeIcon([
  <circle key="a" cx="12" cy="12" r="9" />,
  <path key="b" d="M12 7v6l4 2" />,
]);
export const Compass = makeIcon([
  <circle key="a" cx="12" cy="12" r="9" />,
  <path key="b" d="m15 9-2 6-4 2 2-6z" />,
]);
export const Edit3 = makeIcon([
  <path key="a" d="M4 20h4L19 9l-4-4L4 16z" />,
  <path key="b" d="m13 7 4 4" />,
]);
export const ExternalLink = ArrowUpRight;
export const FileCheck2 = makeIcon([
  <path key="a" d="M6 3h8l4 4v14H6z" />,
  <path key="b" d="M14 3v5h5" />,
  <path key="c" d="m8 15 2 2 5-5" />,
]);
export const FilePenLine = makeIcon([
  <path key="a" d="M6 3h8l4 4v14H6z" />,
  <path key="b" d="M14 3v5h5" />,
  <path key="c" d="M9 17h3l4-4-3-3-4 4z" />,
]);
export const FileText = makeIcon([
  <path key="a" d="M6 3h8l4 4v14H6z" />,
  <path key="b" d="M14 3v5h5M9 12h6M9 16h6" />,
]);
export const FileUp = makeIcon([
  <path key="a" d="M6 3h8l4 4v14H6z" />,
  <path key="b" d="M14 3v5h5M12 17V10M9 13l3-3 3 3" />,
]);
export const Filter = makeIcon([
  <path key="a" d="M4 6h16l-6 7v5l-4 2v-7z" />,
]);
export const Hash = makeIcon([
  <path key="a" d="M9 4 7 20M17 4l-2 16M4 9h16M3 15h16" />,
]);
export const Image = makeIcon([
  <rect key="a" x="4" y="5" width="16" height="14" rx="2" />,
  <circle key="b" cx="9" cy="10" r="1.5" />,
  <path key="c" d="m5 18 5-5 4 4 2-2 3 3" />,
]);
export const Inbox = makeIcon([
  <path key="a" d="M5 4h14l2 9v6H3v-6z" />,
  <path key="b" d="M3 13h5l2 3h4l2-3h5" />,
]);
export const LayoutDashboard = makeIcon([
  <rect key="a" x="4" y="4" width="7" height="7" rx="1" />,
  <rect key="b" x="13" y="4" width="7" height="5" rx="1" />,
  <rect key="c" x="4" y="13" width="7" height="7" rx="1" />,
  <rect key="d" x="13" y="11" width="7" height="9" rx="1" />,
]);
export const Loader2 = makeIcon([
  <path key="a" d="M12 3a9 9 0 1 0 9 9" />,
]);
export const LogIn = makeIcon([
  <path key="a" d="M10 17v2H5V5h5v2" />,
  <path key="b" d="M13 8l4 4-4 4M17 12H8" />,
]);
export const LogOut = makeIcon([
  <path key="a" d="M14 17v2H5V5h9v2" />,
  <path key="b" d="M16 8l4 4-4 4M20 12H9" />,
]);
export const MapPin = makeIcon([
  <path key="a" d="M12 21s7-6 7-12A7 7 0 0 0 5 9c0 6 7 12 7 12z" />,
  <circle key="b" cx="12" cy="9" r="2" />,
]);
export const Megaphone = makeIcon([
  <path key="a" d="M4 13V9h4l10-4v12L8 13z" />,
  <path key="b" d="m7 13 2 6" />,
]);
export const Menu = makeIcon([
  <path key="a" d="M4 7h16M4 12h16M4 17h16" />,
]);
export const Plus = makeIcon([
  <path key="a" d="M12 5v14M5 12h14" />,
]);
export const RefreshCw = makeIcon([
  <path key="a" d="M20 6v5h-5" />,
  <path key="b" d="M4 18v-5h5" />,
  <path key="c" d="M18 10a6 6 0 0 0-10-4L4 10" />,
  <path key="d" d="M6 14a6 6 0 0 0 10 4l4-4" />,
]);
export const Save = makeIcon([
  <path key="a" d="M5 4h12l2 2v14H5z" />,
  <path key="b" d="M8 4v6h8M8 20v-6h8v6" />,
]);
export const Search = makeIcon([
  <circle key="a" cx="11" cy="11" r="6" />,
  <path key="b" d="m16 16 4 4" />,
]);
export const Settings = makeIcon([
  <circle key="a" cx="12" cy="12" r="3" />,
  <path key="b" d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />,
]);
export const Shield = makeIcon([
  <path key="a" d="M12 3 19 6v5c0 5-3 8-7 10-4-2-7-5-7-10V6z" />,
]);
export const ShieldCheck = makeIcon([
  <path key="a" d="M12 3 19 6v5c0 5-3 8-7 10-4-2-7-5-7-10V6z" />,
  <path key="b" d="m8 12 3 3 5-6" />,
]);
export const Sparkles = makeIcon([
  <path key="a" d="M12 3 14 9l6 3-6 3-2 6-2-6-6-3 6-3z" />,
]);
export const Trash2 = makeIcon([
  <path key="a" d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14" />,
  <path key="b" d="M10 11v6M14 11v6" />,
]);
export const User = makeIcon([
  <circle key="a" cx="12" cy="8" r="4" />,
  <path key="b" d="M4 21a8 8 0 0 1 16 0" />,
]);
export const UserPlus = makeIcon([
  <circle key="a" cx="10" cy="8" r="4" />,
  <path key="b" d="M3 21a7 7 0 0 1 14 0M18 8v6M15 11h6" />,
]);
export const Users = makeIcon([
  <circle key="a" cx="9" cy="8" r="3.5" />,
  <path key="b" d="M2.5 21a6.5 6.5 0 0 1 13 0" />,
  <path key="c" d="M16 11a3 3 0 0 0 0-6M17 14a5 5 0 0 1 4 5" />,
]);
export const X = makeIcon([
  <path key="a" d="M6 6l12 12M18 6 6 18" />,
]);
