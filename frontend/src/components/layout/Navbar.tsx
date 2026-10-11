import { Link, NavLink } from "react-router-dom";
import { Zap } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Home" },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/chat", label: "Chat" },
];

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 max-w-screen-2xl items-center mx-auto px-4">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 mr-6 font-bold text-foreground">
          <Zap className="h-5 w-5 text-yellow-400" />
          <span>Hackathon</span>
        </Link>

        {/* Nav links */}
        <nav className="flex items-center gap-1 text-sm">
          {navItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "px-3 py-1.5 rounded-md transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                )
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Right side badge */}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-muted-foreground border border-border rounded-full px-2 py-0.5">
            v0.1.0
          </span>
        </div>
      </div>
    </header>
  );
}
