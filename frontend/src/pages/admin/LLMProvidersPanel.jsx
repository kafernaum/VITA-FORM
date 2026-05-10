import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Trash2, Plus, Check, X, Sparkles, Star, AlertTriangle } from "lucide-react";

const PROVIDER_BADGE = {
  anthropic: { c: "#D97757", l: "Anthropic Claude" },
  openai: { c: "#10B981", l: "OpenAI" },
  google: { c: "#4285F4", l: "Google Gemini" },
  emergent: { c: "#D4AF37", l: "Emergent (proxy)" },
};

export default function LLMProvidersPanel() {
  const [providers, setProviders] = useState([]);
  const [meta, setMeta] = useState({ providers: [], default_models: {} });
  const [testing, setTesting] = useState(null);
  const [form, setForm] = useState({
    provider: "anthropic", api_key: "", model: "", label: "",
    is_default: true, active: true,
  });

  const refresh = () => {
    api.get("/admin/llm-providers").then((r) => setProviders(r.data));
    api.get("/admin/llm-providers/meta").then((r) => setMeta(r.data));
  };
  useEffect(refresh, []);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/admin/llm-providers", form);
      toast.success(`${PROVIDER_BADGE[form.provider]?.l || form.provider} ajouté.`);
      setForm({ provider: "anthropic", api_key: "", model: "", label: "",
                is_default: providers.length === 0, active: true });
      refresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Échec de l'ajout.");
    }
  };

  const toggleDefault = async (p) => {
    try {
      await api.patch(`/admin/llm-providers/${p.id}`, {
        provider: p.provider, api_key: "REPLACE_KEEP", model: p.model,
        label: p.label, is_default: !p.is_default, active: p.active,
      });
      // Re-fetch full provider to keep server-side api_key
      // Simpler approach : call dedicated endpoint
    } catch { toast.error("Pour modifier la clé par défaut, supprimez et recréez le provider."); }
  };
  // Le PATCH actuel exige une vraie api_key (min 10) ; on garde donc le toggle via re-creation.
  // À la place, on fournit un endpoint léger :
  const setActiveDefault = async (p) => {
    // Hack: use PATCH but require user to paste key again? Better: build a dedicated
    // endpoint "/admin/llm-providers/{id}/default" — pour rester simple, on
    // demande à l'admin de cliquer "Définir par défaut" : on lit le secret stocké
    // côté backend en fait PATCH avec n'importe quelle clé suffisante. On va
    // contourner en utilisant la même clé tronquée + un sentinel. Mieux : demander
    // à recréer si besoin de changer la clé.
    const keepKey = prompt(
      "Pour définir ce moteur par défaut, recoller la clé API complète " +
      "(elle n'est jamais affichée en clair pour la sécurité) :",
    );
    if (!keepKey || keepKey.length < 10) return;
    try {
      await api.patch(`/admin/llm-providers/${p.id}`, {
        provider: p.provider, api_key: keepKey, model: p.model,
        label: p.label, is_default: true, active: true,
      });
      toast.success("Moteur par défaut mis à jour.");
      refresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Échec.");
    }
  };

  const del = async (p) => {
    if (!window.confirm(`Supprimer ${p.label || p.provider} ?`)) return;
    await api.delete(`/admin/llm-providers/${p.id}`);
    refresh();
  };

  const runTest = async (p) => {
    setTesting(p.id);
    try {
      const { data } = await api.post(`/admin/llm-providers/${p.id}/test`);
      if (data.status === "ok") {
        toast.success(`✓ ${p.provider}/${data.model} OK : « ${data.sample.slice(0, 80)} »`,
                      { duration: 10000 });
      } else {
        toast.error(`Échec (${data.code}) : ${data.detail}`, { duration: 12000 });
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Test impossible.");
    } finally { setTesting(null); }
  };

  return (
    <div className="grid lg:grid-cols-3 gap-6 mt-6">
      <form onSubmit={submit} className="vf-card p-6 lg:col-span-1 space-y-3"
            data-testid="llm-provider-form">
        <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80 mb-3">
          AJOUTER UN MOTEUR IA
        </div>
        <p className="text-xs text-slate-400 mb-2 leading-relaxed">
          Configurez votre propre clé API (Anthropic, OpenAI ou Google).
          La clé est stockée chiffrée côté serveur et jamais affichée en clair.
          Si aucun moteur n'est actif, VITA-FORM utilise la clé Emergent par défaut.
        </p>

        <div>
          <label className="text-xs text-slate-400">Fournisseur</label>
          <select value={form.provider}
                  onChange={(e) => setForm({ ...form, provider: e.target.value, model: "" })}
                  className="vf-input w-full mt-1 px-3 py-2" data-testid="llm-provider-select">
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="openai">OpenAI (GPT)</option>
            <option value="google">Google (Gemini)</option>
            <option value="emergent">Emergent (universal key)</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-slate-400">Clé API</label>
          <input type="password" required minLength={10}
            placeholder={
              form.provider === "anthropic" ? "sk-ant-..." :
              form.provider === "openai"    ? "sk-..." :
              form.provider === "google"    ? "AIza..." :
              "sk-emergent-..."
            }
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            className="vf-input w-full mt-1 px-3 py-2" data-testid="llm-api-key" />
          <p className="text-[0.65rem] text-slate-500 mt-1">
            {form.provider === "anthropic" && "console.anthropic.com → Settings → API Keys"}
            {form.provider === "openai"    && "platform.openai.com → API keys"}
            {form.provider === "google"    && "aistudio.google.com → Get API key"}
            {form.provider === "emergent"  && "Profile → Universal Key"}
          </p>
        </div>

        <div>
          <label className="text-xs text-slate-400">
            Modèle <span className="text-slate-600">(facultatif)</span>
          </label>
          <input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })}
            placeholder={meta.default_models[form.provider] || ""}
            className="vf-input w-full mt-1 px-3 py-2" data-testid="llm-model" />
        </div>

        <div>
          <label className="text-xs text-slate-400">Étiquette (facultatif)</label>
          <input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })}
            placeholder="Ex : Claude prod"
            className="vf-input w-full mt-1 px-3 py-2" />
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-300 mt-3">
          <input type="checkbox" checked={form.is_default}
            onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
            className="accent-[#D4AF37]" data-testid="llm-default-cb" />
          Définir comme moteur par défaut
        </label>

        <button type="submit"
          className="vf-btn-primary w-full mt-3 inline-flex items-center justify-center gap-2"
          data-testid="llm-submit">
          <Plus className="w-4 h-4" /> Ajouter
        </button>
      </form>

      <div className="lg:col-span-2 space-y-3">
        <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80 mb-1">
          MOTEURS CONFIGURÉS
        </div>

        {providers.length === 0 ? (
          <div className="vf-card p-8 text-center">
            <AlertTriangle className="w-7 h-7 text-[#D4AF37] mx-auto" />
            <p className="text-slate-300 mt-3">
              Aucun moteur IA configuré. VITA-FORM utilise la clé Emergent par défaut
              (peut être saturée). Configurez votre propre clé API pour des
              générations <strong>plus rapides et plus fiables</strong>.
            </p>
          </div>
        ) : (
          providers.map((p) => {
            const badge = PROVIDER_BADGE[p.provider] || { c: "#94A3B8", l: p.provider };
            return (
              <div key={p.id} className="vf-card p-5 flex items-center gap-5"
                   data-testid={`llm-row-${p.id}`}>
                <div className="w-1.5 h-12 rounded" style={{ background: badge.c }} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="vf-serif text-lg text-slate-50">{p.label || badge.l}</span>
                    {p.is_default && (
                      <span className="vf-tag !text-[0.55rem] !border-[#D4AF37] !text-[#D4AF37]">
                        <Star className="w-3 h-3 inline mr-1" /> PAR DÉFAUT
                      </span>
                    )}
                    {!p.active && (
                      <span className="vf-tag !text-[0.55rem] opacity-60">DÉSACTIVÉ</span>
                    )}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {badge.l} · {p.model} · clé {p.api_key_preview}
                  </div>
                </div>
                <button onClick={() => runTest(p)} disabled={testing === p.id}
                  className="vf-btn-ghost !px-3 !py-1.5 text-xs flex items-center gap-1"
                  data-testid={`llm-test-${p.id}`}>
                  <Sparkles className="w-3.5 h-3.5" />
                  {testing === p.id ? "..." : "Tester"}
                </button>
                {!p.is_default && (
                  <button onClick={() => setActiveDefault(p)}
                    className="vf-btn-ghost !px-3 !py-1.5 text-xs"
                    data-testid={`llm-default-${p.id}`}>
                    Définir par défaut
                  </button>
                )}
                <button onClick={() => del(p)} className="text-red-400 hover:text-red-300"
                  data-testid={`llm-del-${p.id}`}>
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
