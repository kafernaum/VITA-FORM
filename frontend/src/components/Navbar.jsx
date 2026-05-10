import { Link, NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/context/AuthContext";
import { Hourglass, LogOut, User2, ShieldCheck } from "lucide-react";
import LanguageSwitcher from "@/components/LanguageSwitcher";

export default function Navbar() {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const nav = useNavigate();

  const navItems = [
    { to: "/theorie", label: t("nav.theorie") },
    { to: "/generator", label: t("nav.generator") },
    { to: "/analyse", label: t("nav.analyse") },
    { to: "/library", label: t("nav.library") },
    { to: "/auteur", label: t("nav.auteur") },
  ];

  return (
    <nav className="vf-glass fixed top-0 left-0 right-0 z-50" data-testid="main-navbar">
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group" data-testid="nav-logo">
          <Hourglass className="w-6 h-6 text-[#D4AF37] group-hover:rotate-12 transition-transform" />
          <div className="leading-tight">
            <div className="vf-serif text-xl tracking-wide text-slate-50">VITA-FORM</div>
            <div className="vf-mono text-[0.6rem] tracking-[0.3em] text-[#D4AF37]/80">DOCTRINA · VITALIS</div>
          </div>
        </Link>

        <div className="hidden md:flex items-center gap-7">
          {navItems.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              data-testid={`nav-${it.to.replace("/", "")}`}
              className={({ isActive }) =>
                `text-sm tracking-wide transition-colors ${
                  isActive ? "text-[#D4AF37]" : "text-slate-300 hover:text-[#F3E5AB]"
                }`
              }
            >
              {it.label}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink to="/admin" data-testid="nav-admin"
              className="text-sm tracking-wide text-[#D4AF37] flex items-center gap-1">
              <ShieldCheck className="w-4 h-4" /> {t("nav.admin")}
            </NavLink>
          )}
        </div>

        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          {user ? (
            <>
              <span className="hidden sm:flex items-center gap-2 text-sm text-slate-300" data-testid="user-badge">
                <User2 className="w-4 h-4 text-[#D4AF37]" />
                {user.full_name}
                {user.vip && <span className="vf-tag !py-0.5 !text-[0.55rem]">VIP</span>}
              </span>
              <button
                data-testid="logout-button"
                onClick={() => { logout(); nav("/"); }}
                className="vf-btn-ghost !px-3 !py-2 flex items-center gap-2"
              >
                <LogOut className="w-4 h-4" /> <span className="hidden sm:inline">{t("nav.logout")}</span>
              </button>
            </>
          ) : (
            <>
              <Link to="/auth" data-testid="nav-login" className="vf-btn-ghost text-sm">{t("nav.login")}</Link>
              <Link to="/auth?tab=register" data-testid="nav-register" className="vf-btn-primary text-sm hidden sm:inline-block">
                {t("nav.register")}
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
