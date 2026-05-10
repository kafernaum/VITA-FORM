import { useTranslation } from "react-i18next";
import { Languages } from "lucide-react";

const LANGS = [
  { code: "fr", label: "FR" },
  { code: "ar", label: "AR" },
];

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = (i18n.resolvedLanguage || i18n.language || "fr").split("-")[0];

  return (
    <div
      data-testid="language-switcher"
      className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-1"
      aria-label="Language switcher"
    >
      <Languages className="w-3.5 h-3.5 text-[#D4AF37]" aria-hidden />
      {LANGS.map((l) => {
        const active = current === l.code;
        return (
          <button
            key={l.code}
            type="button"
            onClick={() => i18n.changeLanguage(l.code)}
            data-testid={`lang-btn-${l.code}`}
            aria-pressed={active}
            className={`px-2 py-0.5 text-[0.7rem] tracking-[0.2em] vf-mono rounded-full transition ${
              active
                ? "bg-[#D4AF37] text-[#0A1128]"
                : "text-slate-300 hover:text-[#F3E5AB]"
            }`}
          >
            {l.label}
          </button>
        );
      })}
    </div>
  );
}
