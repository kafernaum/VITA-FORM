import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Hourglass } from "lucide-react";

export default function Auth() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const initialTab = params.get("tab") === "register" ? "register" : "login";
  const next = params.get("next") || "/generator";
  const [tab, setTab] = useState(initialTab);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login, register } = useAuth();
  const nav = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (tab === "login") {
        await login(email, password);
        toast.success(t("auth.loginSuccess"));
      } else {
        await register(email, password, fullName);
        toast.success(t("auth.registerSuccess"));
      }
      nav(next);
    } catch (err) {
      const msg = err?.response?.data?.detail || t("auth.errorGeneric");
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-16 grid lg:grid-cols-2 gap-14 items-center">
      <div className="hidden lg:block vf-fade-up">
        <span className="vf-tag">{t("landing.tag")}</span>
        <h1 className="vf-serif text-4xl sm:text-5xl mt-5 text-slate-50">
          {t("landing.title")}
        </h1>
        <p className="text-slate-300 mt-6 leading-relaxed">
          {t("landing.subtitle")}
        </p>
        <div className="mt-10 vf-frame bg-[#0F1730]/60">
          <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">VITA-FORM</div>
          <p className="vf-serif text-xl text-slate-100 mt-4 italic">
            {t("footer.quote")}
          </p>
        </div>
      </div>

      <div className="vf-card p-8 lg:p-10 vf-fade-up vf-delay-100" data-testid="auth-card">
        <div className="flex items-center gap-3 mb-7">
          <Hourglass className="w-6 h-6 text-[#D4AF37]" />
          <div>
            <div className="vf-serif text-2xl text-slate-50">
              {tab === "login" ? t("auth.loginTab") : t("auth.registerTab")}
            </div>
            <div className="text-xs text-slate-400 mt-0.5">VITA-FORM · DOCTRINA · VITALIS</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-6">
          <button
            data-testid="tab-login"
            onClick={() => setTab("login")}
            className={`py-2 text-sm border ${tab === "login" ? "border-[#D4AF37] text-[#D4AF37]" : "border-[#1E293B] text-slate-400"}`}
          >{t("auth.loginTab")}</button>
          <button
            data-testid="tab-register"
            onClick={() => setTab("register")}
            className={`py-2 text-sm border ${tab === "register" ? "border-[#D4AF37] text-[#D4AF37]" : "border-[#1E293B] text-slate-400"}`}
          >{t("auth.registerTab")}</button>
        </div>

        <form onSubmit={submit} className="space-y-4">
          {tab === "register" && (
            <div>
              <label className="text-xs text-slate-400 vf-mono tracking-[0.2em]">{t("auth.fullName")}</label>
              <input
                data-testid="register-fullname"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required minLength={2}
                placeholder="—"
                className="vf-input w-full mt-1.5 px-3 py-2.5"
              />
            </div>
          )}
          <div>
            <label className="text-xs text-slate-400 vf-mono tracking-[0.2em]">{t("auth.email")}</label>
            <input
              type="email" data-testid="auth-email" required
              value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="—@—"
              className="vf-input w-full mt-1.5 px-3 py-2.5"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 vf-mono tracking-[0.2em]">{t("auth.password")}</label>
            <input
              type="password" data-testid="auth-password" required minLength={6}
              value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="vf-input w-full mt-1.5 px-3 py-2.5"
            />
          </div>
          <button
            type="submit" disabled={submitting}
            data-testid="auth-submit"
            className="vf-btn-primary w-full mt-4"
          >
            {submitting ? "..." : (tab === "login" ? t("auth.loginButton") : t("auth.registerButton"))}
          </button>
        </form>

        <Link to="/" className="block text-center text-xs text-slate-500 mt-6 hover:text-[#D4AF37]">
          {t("common.back")}
        </Link>
      </div>
    </div>
  );
}
