import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, API } from "@/lib/api";
import { renderMarkdown } from "@/lib/markdown";
import { toast } from "sonner";
import { Lock, Download, FileText, FileType2, Presentation, CheckCircle2,
         ExternalLink, Building2, Copy, Check } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";

const CURRENCY_LABELS = {
  EUR: "🇪🇺 EUR", USD: "🇺🇸 USD", GBP: "🇬🇧 GBP",
  CAD: "🇨🇦 CAD", CHF: "🇨🇭 CHF", AUD: "🇦🇺 AUD", JPY: "🇯🇵 JPY",
};

function CopyField({ label, value, testid }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(value || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="flex items-baseline justify-between gap-3 border border-[#1E293B] px-3 py-2 text-sm">
      <span className="text-slate-400 text-xs vf-mono tracking-[0.15em]">{label}</span>
      <span className="text-slate-100 vf-mono flex-1 text-right truncate" data-testid={testid}>{value || "—"}</span>
      <button onClick={copy} type="button" className="text-[#D4AF37] hover:text-[#F3E5AB]">
        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
      </button>
    </div>
  );
}

export default function Preview() {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [paywallOpen, setPaywallOpen] = useState(false);
  const [paying, setPaying] = useState(false);
  const [tab, setTab] = useState("paypal");
  const [currency, setCurrency] = useState("EUR");
  const [pricing, setPricing] = useState({ currencies: ["EUR"], prices: { EUR: 14.90 } });
  // Wire state
  const [bankAccounts, setBankAccounts] = useState([]);
  const [bankId, setBankId] = useState("");
  const [wireTxn, setWireTxn] = useState(null);
  const [wireRef, setWireRef] = useState("");
  const [wireSender, setWireSender] = useState("");
  const [wireNote, setWireNote] = useState("");
  const [confirming, setConfirming] = useState(false);

  const load = () => {
    api.get(`/generations/${id}`).then((r) => setDoc(r.data)).finally(() => setLoading(false));
  };
  useEffect(load, [id]);

  // Polling tant que le livrable est en cours de génération (status==='pending').
  // Le serveur génère en arrière-plan via Anthropic/OpenAI/Gemini — on
  // interroge /status toutes les 4s.
  useEffect(() => {
    if (!doc || doc.status !== "pending") return undefined;
    let stopped = false;
    const poll = async () => {
      try {
        const { data } = await api.get(`/generations/${id}/status`);
        if (stopped) return;
        if (data.status === "ready") {
          toast.success("Livrable prêt.");
          load();
        } else if (data.status === "failed") {
          toast.error(data.error_detail || "Échec de génération.",
                      { duration: 15000 });
          load();
        } else {
          setTimeout(poll, 4000);
        }
      } catch {
        if (!stopped) setTimeout(poll, 6000);
      }
    };
    setTimeout(poll, 3000);
    return () => { stopped = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc?.status, id]);

  useEffect(() => {
    api.get("/payments/options").then((r) => {
      setPricing(r.data);
      setCurrency(r.data.default_currency || "EUR");
    }).catch(() => {});
    api.get("/bank-accounts").then((r) => {
      setBankAccounts(r.data);
      if (r.data.length) setBankId(r.data[0].id);
    }).catch(() => {});
  }, []);

  const download = async (fmt) => {
    if (!doc?.unlocked) { setPaywallOpen(true); return; }
    try {
      const token = localStorage.getItem("vf_token");
      const res = await fetch(`${API}/generations/${id}/download/${fmt}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Téléchargement refusé");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `vitaform-${id.slice(0,8)}.${fmt === "slides" ? "html" : fmt}`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch { toast.error("Échec du téléchargement."); }
  };

  const checkoutPaypal = async () => {
    setPaying(true);
    try {
      const { data } = await api.post("/payments/checkout", {
        generation_id: id, origin_url: window.location.origin, currency,
      });
      window.location.href = data.url;
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Initialisation du paiement impossible.");
      setPaying(false);
    }
  };

  const initiateWire = async () => {
    if (!bankId) { toast.error("Aucun compte bancaire actif."); return; }
    setPaying(true);
    try {
      const { data } = await api.post("/payments/wire/initiate", {
        generation_id: id, bank_account_id: bankId, currency,
      });
      setWireTxn(data);
      toast.success("Coordonnées générées. Effectuez le virement puis confirmez ci-dessous.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Échec d'initiation.");
    } finally { setPaying(false); }
  };

  const confirmWire = async () => {
    if (!wireRef || !wireSender) { toast.error("Référence et nom de l'émetteur requis."); return; }
    setConfirming(true);
    try {
      await api.post(`/payments/wire/${wireTxn.txn_id}/confirm`, {
        reference: wireRef, sender_name: wireSender, sender_note: wireNote,
      });
      toast.success("Déclaration enregistrée. L'administrateur valide sous 24-72 h.");
      setPaywallOpen(false);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Échec de la déclaration.");
    } finally { setConfirming(false); }
  };

  if (loading) return <div className="max-w-5xl mx-auto px-6 py-20 text-slate-400">Chargement…</div>;
  if (!doc) return <div className="max-w-5xl mx-auto px-6 py-20 text-slate-400">Livrable introuvable.</div>;

  const price = pricing.prices?.[currency] ?? 14.90;
  const priceLabel = currency === "JPY" ? `${price} ${currency}` : `${price.toFixed(2)} ${currency}`;
  const selectedBank = bankAccounts.find((b) => b.id === bankId);

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-12 py-12">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <span className="vf-tag" data-testid="preview-kind">
            {doc.kind === "vitalist_analysis" ? "Analyse vitaliste" : "Parcours académique"}
          </span>
          <h1 className="vf-serif text-3xl sm:text-4xl mt-4 text-slate-50">{doc.topic}</h1>
          <div className="text-sm text-slate-400 mt-2">{doc.institution_name} · {doc.cycle} · {doc.duration}</div>
        </div>
        <div className="flex items-center gap-3">
          {doc.unlocked ? (
            <span className="text-sm text-emerald-300 flex items-center gap-2" data-testid="unlocked-badge">
              <CheckCircle2 className="w-4 h-4" /> Livrable débloqué
            </span>
          ) : (
            <span className="text-sm text-[#D4AF37] flex items-center gap-2" data-testid="locked-badge">
              <Lock className="w-4 h-4" /> Aperçu watermarqué
            </span>
          )}
        </div>
      </div>

      {doc.metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
          {[
            { l: "Montant", v: `${doc.metrics.monetary_amount.toLocaleString("fr-FR")} ${doc.metrics.currency}` },
            { l: "Jours-vie", v: doc.metrics.life_days.toLocaleString("fr-FR") },
            { l: "Mois-vie", v: doc.metrics.life_months.toLocaleString("fr-FR") },
            { l: "Années-vie", v: doc.metrics.life_years.toLocaleString("fr-FR") },
          ].map((m) => (
            <div key={m.l} className="vf-card p-5" data-testid={`metric-${m.l.toLowerCase()}`}>
              <div className="vf-mono text-[0.65rem] tracking-[0.25em] text-[#D4AF37]/80">{m.l.toUpperCase()}</div>
              <div className="vf-serif text-2xl mt-2 text-[#F3E5AB]">{m.v}</div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-10 grid lg:grid-cols-4 gap-8">
        <article className={`lg:col-span-3 vf-card p-8 ${doc.unlocked ? "" : "vf-watermark"}`}>
          {doc.status === "pending" ? (
            <div className="py-16 text-center" data-testid="preview-pending">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-2 border-[#D4AF37] border-t-transparent" />
              <div className="vf-serif text-2xl text-slate-100 mt-8">
                {doc.language === "ar"
                  ? "جارٍ توليد مادتك الحيوية…"
                  : "Génération de votre livrable vitaliste en cours…"}
              </div>
              <p className="text-slate-400 mt-3 max-w-md mx-auto leading-relaxed">
                {doc.language === "ar"
                  ? "العملية تتم في الخلفية. يمكنك مغادرة الصفحة والعودة لاحقًا — ستجد المادة في مكتبتك. الزمن المتوقع: 30-90 ثانية."
                  : "Le traitement s'effectue en arrière-plan. Vous pouvez fermer cette page et revenir plus tard — le livrable sera dans votre bibliothèque. Temps estimé : 30 à 90 secondes."}
              </p>
            </div>
          ) : doc.status === "failed" ? (
            <div className="py-16 text-center" data-testid="preview-failed">
              <div className="vf-serif text-2xl text-red-300">
                {doc.language === "ar" ? "فشل التوليد" : "Génération échouée"}
              </div>
              <p className="text-slate-400 mt-3 max-w-md mx-auto">
                {doc.error_detail || "Erreur inconnue."}
              </p>
              <p className="text-slate-500 mt-2 text-xs">
                Vérifiez le moteur IA dans <code>/admin → Moteurs IA</code> ou
                rechargez votre crédit auprès du provider.
              </p>
            </div>
          ) : (
            <div className="vf-prose relative z-0"
              dir={doc.language === "ar" ? "rtl" : "ltr"}
              lang={doc.language || "fr"}
              dangerouslySetInnerHTML={{ __html: renderMarkdown(doc.content) }}
              data-testid="preview-content" />
          )}
        </article>

        <aside className="space-y-4">
          <div className="vf-frame bg-[#0F1730]/60">
            <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">EXPORTS ACADÉMIQUES</div>
            <div className="space-y-3 mt-5">
              {[
                { fmt: "pdf", icon: FileText, label: "Télécharger PDF" },
                { fmt: "docx", icon: FileType2, label: "Télécharger Word (.docx)" },
                { fmt: "slides", icon: Presentation, label: "Télécharger Slides (HTML)" },
              ].map((b) => (
                <button key={b.fmt} onClick={() => download(b.fmt)}
                  data-testid={`download-${b.fmt}`}
                  className="vf-btn-ghost w-full flex items-center justify-between">
                  <span className="flex items-center gap-2"><b.icon className="w-4 h-4" /> {b.label}</span>
                  {!doc.unlocked && <Lock className="w-3.5 h-3.5" />}
                  {doc.unlocked && <Download className="w-3.5 h-3.5" />}
                </button>
              ))}
            </div>
            {!doc.unlocked && (
              <button onClick={() => setPaywallOpen(true)}
                data-testid="open-paywall-btn"
                className="vf-btn-primary w-full mt-6">
                Débloquer · {priceLabel}
              </button>
            )}
          </div>
        </aside>
      </div>

      <Dialog open={paywallOpen} onOpenChange={setPaywallOpen}>
        <DialogContent className="bg-[#131B33] border border-[#D4AF37]/40 text-slate-100 max-w-lg">
          <DialogHeader>
            <DialogTitle className="vf-serif text-2xl text-slate-50">Choisissez votre mode de paiement</DialogTitle>
            <DialogDescription className="text-slate-400">
              Paiement instantané par PayPal/carte bancaire, ou virement bancaire (validation manuelle 24-72h).
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-2 mb-2">
            <button onClick={() => setTab("paypal")} data-testid="tab-paypal"
              className={`py-3 text-sm border ${tab === "paypal" ? "border-[#D4AF37] text-[#D4AF37]" : "border-[#1E293B] text-slate-400"}`}>
              <span className="font-bold">PayPal</span> · Carte
            </button>
            <button onClick={() => setTab("wire")} data-testid="tab-wire"
              className={`py-3 text-sm border ${tab === "wire" ? "border-[#D4AF37] text-[#D4AF37]" : "border-[#1E293B] text-slate-400"}`}>
              <Building2 className="inline w-4 h-4 mr-1" /> Virement bancaire
            </button>
          </div>

          {/* Currency selector commun aux 2 onglets */}
          <div>
            <div className="vf-mono text-[0.65rem] tracking-[0.25em] text-[#D4AF37]/80 mb-2">DEVISE</div>
            <div className="grid grid-cols-4 gap-2">
              {pricing.currencies?.map((c) => (
                <button key={c} onClick={() => setCurrency(c)}
                  data-testid={`paywall-currency-${c}`}
                  className={`py-2 px-2 text-xs border ${currency === c
                    ? "border-[#D4AF37] text-[#D4AF37] bg-[#D4AF37]/5"
                    : "border-[#1E293B] text-slate-400 hover:text-slate-200"}`}>
                  {CURRENCY_LABELS[c] || c}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-baseline justify-between border border-[#D4AF37]/30 px-4 py-3 mt-1">
            <span className="text-sm">Livrable VITA-FORM (PDF + Word + Slides)</span>
            <span className="text-[#D4AF37] vf-mono text-lg" data-testid="paywall-amount">{priceLabel}</span>
          </div>

          {/* Onglet PAYPAL */}
          {tab === "paypal" && (
            <>
              <p className="text-xs text-slate-500">
                Vous serez redirigé vers PayPal. Paiement par compte PayPal <strong>ou par carte
                bancaire en mode invité</strong> (sans création de compte).
              </p>
              <DialogFooter>
                <button onClick={() => setPaywallOpen(false)} className="vf-btn-ghost">Annuler</button>
                <button onClick={checkoutPaypal} disabled={paying}
                  className="vf-btn-primary inline-flex items-center gap-2"
                  data-testid="paywall-confirm"
                  style={{ background: "#0070BA", color: "#fff", borderColor: "#0070BA" }}>
                  {paying ? "Redirection…" : (
                    <><span className="font-bold">PayPal</span> Payer {priceLabel} <ExternalLink className="w-3.5 h-3.5" /></>
                  )}
                </button>
              </DialogFooter>
            </>
          )}

          {/* Onglet VIREMENT */}
          {tab === "wire" && !wireTxn && (
            <>
              {bankAccounts.length === 0 ? (
                <p className="text-sm text-amber-300 italic">
                  Aucun compte bancaire actif n'est configuré pour le moment. Contactez l'administrateur ou utilisez PayPal.
                </p>
              ) : (
                <>
                  <div>
                    <div className="vf-mono text-[0.65rem] tracking-[0.25em] text-[#D4AF37]/80 mb-2">COMPTE BÉNÉFICIAIRE</div>
                    <select value={bankId} onChange={(e) => setBankId(e.target.value)}
                      data-testid="wire-bank-select"
                      className="vf-input w-full px-3 py-2.5">
                      {bankAccounts.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.bank_name} · {b.holder_name} ({b.currency})
                        </option>
                      ))}
                    </select>
                  </div>
                  {selectedBank && (
                    <div className="space-y-1 mt-2 text-xs">
                      <CopyField label="IBAN" value={selectedBank.iban} testid="wire-iban" />
                      <CopyField label="BIC/SWIFT" value={selectedBank.bic} testid="wire-bic" />
                      <CopyField label="Bénéficiaire" value={selectedBank.holder_name} />
                      <CopyField label="Banque" value={selectedBank.bank_name} />
                    </div>
                  )}
                  <DialogFooter>
                    <button onClick={() => setPaywallOpen(false)} className="vf-btn-ghost">Annuler</button>
                    <button onClick={initiateWire} disabled={paying || !bankId}
                      data-testid="wire-initiate-btn"
                      className="vf-btn-primary inline-flex items-center gap-2">
                      {paying ? "..." : "Obtenir une référence de virement"}
                    </button>
                  </DialogFooter>
                </>
              )}
            </>
          )}

          {/* Étape de confirmation virement */}
          {tab === "wire" && wireTxn && (
            <>
              <div className="vf-frame bg-[#0F1730]/80 mt-2">
                <div className="vf-mono text-[0.65rem] tracking-[0.25em] text-[#D4AF37]/80">RÉFÉRENCE OBLIGATOIRE</div>
                <div className="vf-serif text-2xl text-[#F3E5AB] mt-2 vf-mono" data-testid="wire-ref-display">
                  {wireTxn.wire_reference}
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  Recopiez cette référence dans le libellé de votre virement de
                  <strong className="text-slate-100"> {priceLabel}</strong>. Sans elle, le rapprochement est impossible.
                </p>
              </div>
              <p className="text-xs text-slate-300 mt-2">
                Une fois le virement émis, déclarez-le ci-dessous :
              </p>
              <input value={wireSender} onChange={(e) => setWireSender(e.target.value)}
                placeholder="Nom de l'émetteur (compte source)"
                data-testid="wire-sender-input"
                className="vf-input w-full px-3 py-2.5" />
              <input value={wireRef} onChange={(e) => setWireRef(e.target.value)}
                placeholder="Référence de votre virement (donnée par votre banque)"
                data-testid="wire-bankref-input"
                className="vf-input w-full px-3 py-2.5" />
              <textarea value={wireNote} onChange={(e) => setWireNote(e.target.value)}
                placeholder="Note (optionnel)" rows={2}
                className="vf-input w-full px-3 py-2.5 resize-none text-sm" />
              <DialogFooter>
                <button onClick={() => setPaywallOpen(false)} className="vf-btn-ghost">Plus tard</button>
                <button onClick={confirmWire} disabled={confirming}
                  data-testid="wire-confirm-btn"
                  className="vf-btn-primary inline-flex items-center gap-2">
                  {confirming ? "..." : "J'ai effectué le virement"}
                </button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
