import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Crown, Trash2, Plus, Users2, FileSignature, BadgeDollarSign,
         Building2, Landmark, BarChart3, Check, X } from "lucide-react";
import LLMProvidersPanel from "@/pages/admin/LLMProvidersPanel";

export default function Admin() {
  const [tab, setTab] = useState("users");
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [generations, setGenerations] = useState([]);
  const [institutions, setInstitutions] = useState([]);
  const [jurisprudences, setJurisprudences] = useState([]);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [pendingPayments, setPendingPayments] = useState([]);
  const [revenue, setRevenue] = useState({ by_currency: {}, by_month: [], transactions_total: 0 });
  const [newInst, setNewInst] = useState({ name: "", country: "France", country_code: "FR", city: "", type: "ENA" });
  const [newJur, setNewJur] = useState({ title: "", country: "France", reference: "", body: "", tags: "" });
  const [newBank, setNewBank] = useState({
    holder_name: "", bank_name: "", iban: "", bic: "",
    currency: "EUR", country: "France", instructions: "", is_active: true,
  });

  const refresh = () => {
    api.get("/admin/stats").then((r) => setStats(r.data));
    api.get("/admin/users").then((r) => setUsers(r.data));
    api.get("/admin/generations").then((r) => setGenerations(r.data));
    api.get("/institutions").then((r) => setInstitutions(r.data));
    api.get("/jurisprudences", { params: { limit: 100 } }).then((r) => setJurisprudences(r.data));
    api.get("/admin/bank-accounts").then((r) => setBankAccounts(r.data));
    api.get("/admin/payments/pending").then((r) => setPendingPayments(r.data));
    api.get("/admin/revenue").then((r) => setRevenue(r.data));
  };
  useEffect(refresh, []);

  const toggleVip = async (u) => {
    try {
      await api.post(`/admin/users/${u.id}/vip?vip=${!u.vip}`);
      toast.success(`VIP ${!u.vip ? "activé" : "désactivé"} pour ${u.email}`);
      refresh();
    } catch { toast.error("Échec de la mise à jour."); }
  };

  const addInst = async (e) => {
    e.preventDefault();
    try {
      await api.post("/admin/institutions", newInst);
      toast.success("Institution ajoutée.");
      setNewInst({ name: "", country: "France", country_code: "FR", city: "", type: "ENA" });
      refresh();
    } catch { toast.error("Échec création."); }
  };
  const removeInst = async (id) => {
    if (!window.confirm("Supprimer définitivement ?")) return;
    await api.delete(`/admin/institutions/${id}`);
    toast.success("Supprimée.");
    refresh();
  };

  const addJuris = async (e) => {
    e.preventDefault();
    try {
      await api.post("/admin/jurisprudences", {
        ...newJur,
        tags: newJur.tags ? newJur.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
      });
      toast.success("Jurisprudence ajoutée.");
      setNewJur({ title: "", country: "France", reference: "", body: "", tags: "" });
      refresh();
    } catch { toast.error("Échec création."); }
  };
  const removeJuris = async (id) => {
    if (!window.confirm("Supprimer ?")) return;
    await api.delete(`/admin/jurisprudences/${id}`);
    toast.success("Supprimée.");
    refresh();
  };

  const addBank = async (e) => {
    e.preventDefault();
    try {
      await api.post("/admin/bank-accounts", newBank);
      toast.success("Compte bancaire ajouté.");
      setNewBank({ holder_name: "", bank_name: "", iban: "", bic: "", currency: "EUR",
                    country: "France", instructions: "", is_active: true });
      refresh();
    } catch { toast.error("Échec création."); }
  };
  const toggleBankActive = async (b) => {
    try {
      await api.patch(`/admin/bank-accounts/${b.id}`, { ...b, is_active: !b.is_active });
      toast.success(b.is_active ? "Désactivé." : "Activé.");
      refresh();
    } catch { toast.error("Échec MAJ."); }
  };
  const removeBank = async (id) => {
    if (!window.confirm("Supprimer ce compte ?")) return;
    await api.delete(`/admin/bank-accounts/${id}`);
    toast.success("Supprimé.");
    refresh();
  };
  const validateWire = async (txn_id) => {
    if (!window.confirm("Confirmer la réception du virement ? Le livrable sera débloqué et l'apprenant notifié par email.")) return;
    try {
      await api.post(`/admin/payments/${txn_id}/validate`);
      toast.success("Virement validé. Livrable débloqué.");
      refresh();
    } catch { toast.error("Échec validation."); }
  };
  const rejectWire = async (txn_id) => {
    const reason = window.prompt("Motif de rejet ?", "");
    if (reason === null) return;
    try {
      await api.post(`/admin/payments/${txn_id}/reject?reason=${encodeURIComponent(reason)}`);
      toast.success("Rejeté.");
      refresh();
    } catch { toast.error("Échec rejet."); }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
      <span className="vf-tag">Tableau de bord SuperAdmin</span>
      <h1 className="vf-serif text-4xl sm:text-5xl mt-4 text-slate-50">Administration VITA-FORM</h1>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-10">
          {[
            { l: "Utilisateurs", v: stats.users, i: Users2 },
            { l: "Livrables", v: stats.generations, i: FileSignature },
            { l: "Paiements", v: stats.payments, i: BadgeDollarSign },
            { l: "Institutions", v: stats.institutions, i: Building2 },
          ].map((s) => (
            <div key={s.l} className="vf-card p-5 flex items-center gap-4" data-testid={`stat-${s.l.toLowerCase()}`}>
              <s.i className="w-7 h-7 text-[#D4AF37]" />
              <div>
                <div className="vf-mono text-[0.65rem] tracking-[0.25em] text-slate-400">{s.l.toUpperCase()}</div>
                <div className="vf-serif text-3xl text-slate-50">{s.v}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 mt-12 border-b border-[#1E293B]">
        {[
          { k: "users", l: "Utilisateurs" },
          { k: "generations", l: "Livrables" },
          { k: "institutions", l: "Institutions" },
          { k: "jurisprudences", l: "Jurisprudences" },
          { k: "banks", l: "Comptes bancaires" },
          { k: "pending", l: `Virements en attente${pendingPayments.length ? ` (${pendingPayments.length})` : ""}` },
          { k: "revenue", l: "Recettes" },
          { k: "llm", l: "Moteurs IA" },
        ].map((t) => (
          <button
            key={t.k} onClick={() => setTab(t.k)}
            data-testid={`admin-tab-${t.k}`}
            className={`px-4 py-3 text-sm tracking-wide border-b-2 transition-colors ${
              tab === t.k ? "border-[#D4AF37] text-[#D4AF37]" : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >{t.l}</button>
        ))}
      </div>

      {tab === "users" && (
        <div className="vf-card mt-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-[#0F1730] text-[#D4AF37]">
              <tr><th className="text-left p-3">Utilisateur</th><th>Rôle</th><th>VIP</th><th>Livrables</th><th>Paiements</th><th>Action</th></tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-[#1E293B]" data-testid={`admin-user-${u.id}`}>
                  <td className="p-3">
                    <div className="text-slate-50">{u.full_name}</div>
                    <div className="text-xs text-slate-500">{u.email}</div>
                  </td>
                  <td className="text-center text-slate-300">{u.role}</td>
                  <td className="text-center">
                    {u.vip ? <span className="vf-tag text-[#D4AF37]">VIP</span> : <span className="text-slate-500 text-xs">—</span>}
                  </td>
                  <td className="text-center text-slate-300">{u.generations_count}</td>
                  <td className="text-center text-slate-300">{u.payments_count}</td>
                  <td className="text-center">
                    <button
                      onClick={() => toggleVip(u)}
                      data-testid={`vip-toggle-${u.id}`}
                      className="vf-btn-ghost !px-3 !py-1.5 text-xs inline-flex items-center gap-1"
                    >
                      <Crown className="w-3.5 h-3.5" /> {u.vip ? "Retirer VIP" : "Octroyer VIP"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "generations" && (
        <div className="vf-card mt-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-[#0F1730] text-[#D4AF37]">
              <tr><th className="text-left p-3">Sujet</th><th>Type</th><th>Institution</th><th>Date</th><th>Payé</th></tr>
            </thead>
            <tbody>
              {generations.map((g) => (
                <tr key={g.id} className="border-t border-[#1E293B]" data-testid={`admin-gen-${g.id}`}>
                  <td className="p-3 text-slate-100">{g.topic}</td>
                  <td className="text-slate-300 text-center">{g.kind}</td>
                  <td className="text-slate-300">{g.institution_name}</td>
                  <td className="text-slate-400 text-xs">{new Date(g.created_at).toLocaleDateString("fr-FR")}</td>
                  <td className="text-center">{g.paid ? "✓" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "institutions" && (
        <div className="grid lg:grid-cols-3 gap-6 mt-6">
          <form onSubmit={addInst} className="vf-card p-6 space-y-3" data-testid="admin-add-inst">
            <div className="vf-serif text-xl text-slate-50">Ajouter une institution</div>
            <input required placeholder="Nom" value={newInst.name}
              onChange={(e) => setNewInst({ ...newInst, name: e.target.value })}
              className="vf-input w-full px-3 py-2.5" />
            <input required placeholder="Pays" value={newInst.country}
              onChange={(e) => setNewInst({ ...newInst, country: e.target.value })}
              className="vf-input w-full px-3 py-2.5" />
            <input required placeholder="Code (ex. FR)" maxLength={2} value={newInst.country_code}
              onChange={(e) => setNewInst({ ...newInst, country_code: e.target.value.toUpperCase() })}
              className="vf-input w-full px-3 py-2.5 uppercase" />
            <input required placeholder="Ville" value={newInst.city}
              onChange={(e) => setNewInst({ ...newInst, city: e.target.value })}
              className="vf-input w-full px-3 py-2.5" />
            <select value={newInst.type} onChange={(e) => setNewInst({ ...newInst, type: e.target.value })}
              className="vf-input w-full px-3 py-2.5">
              {["ENA", "ENFIP", "Université", "Institut"].map((t) => <option key={t}>{t}</option>)}
            </select>
            <button type="submit" className="vf-btn-primary w-full inline-flex items-center justify-center gap-2">
              <Plus className="w-4 h-4" /> Ajouter
            </button>
          </form>

          <div className="lg:col-span-2 vf-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[#0F1730] text-[#D4AF37]">
                <tr><th className="text-left p-3">Nom</th><th>Pays</th><th>Type</th><th>Ville</th><th></th></tr>
              </thead>
              <tbody>
                {institutions.map((i) => (
                  <tr key={i.id} className="border-t border-[#1E293B]">
                    <td className="p-3 text-slate-100">{i.name}</td>
                    <td className="text-slate-300 text-center">{i.country}</td>
                    <td className="text-slate-300 text-center">{i.type}</td>
                    <td className="text-slate-400 text-center">{i.city}</td>
                    <td className="text-center">
                      <button
                        onClick={() => removeInst(i.id)} data-testid={`del-inst-${i.id}`}
                        className="text-red-400 hover:text-red-300"
                      ><Trash2 className="w-4 h-4" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {tab === "jurisprudences" && (
        <div className="grid lg:grid-cols-3 gap-6 mt-6">
          <form onSubmit={addJuris} className="vf-card p-6 space-y-3" data-testid="admin-add-juris">
            <div className="vf-serif text-xl text-slate-50">Ajouter une jurisprudence</div>
            <input required placeholder="Intitulé (ex. CC, déc. 2024-845 DC)" value={newJur.title}
              onChange={(e) => setNewJur({ ...newJur, title: e.target.value })}
              className="vf-input w-full px-3 py-2.5" />
            <input required placeholder="Pays" value={newJur.country}
              onChange={(e) => setNewJur({ ...newJur, country: e.target.value })}
              className="vf-input w-full px-3 py-2.5" />
            <input placeholder="Référence officielle" value={newJur.reference}
              onChange={(e) => setNewJur({ ...newJur, reference: e.target.value })}
              className="vf-input w-full px-3 py-2.5" />
            <textarea required minLength={20} rows={6} placeholder="Texte intégral / extrait pertinent…"
              value={newJur.body}
              onChange={(e) => setNewJur({ ...newJur, body: e.target.value })}
              className="vf-input w-full px-3 py-2.5 resize-y" />
            <input placeholder="Tags (séparés par virgules)" value={newJur.tags}
              onChange={(e) => setNewJur({ ...newJur, tags: e.target.value })}
              className="vf-input w-full px-3 py-2.5" />
            <button type="submit" className="vf-btn-primary w-full inline-flex items-center justify-center gap-2">
              <Plus className="w-4 h-4" /> Ajouter
            </button>
          </form>

          <div className="lg:col-span-2 vf-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[#0F1730] text-[#D4AF37]">
                <tr><th className="text-left p-3">Titre</th><th>Pays</th><th>Référence</th><th></th></tr>
              </thead>
              <tbody>
                {jurisprudences.length === 0 && (
                  <tr><td colSpan={4} className="p-6 text-center text-slate-500">
                    Aucune jurisprudence indexée. Importez votre corpus pour activer le RAG.
                  </td></tr>
                )}
                {jurisprudences.map((j) => (
                  <tr key={j.id} className="border-t border-[#1E293B]" data-testid={`admin-juris-${j.id}`}>
                    <td className="p-3 text-slate-100">{j.title}</td>
                    <td className="text-slate-300 text-center">{j.country}</td>
                    <td className="text-slate-400 text-xs">{j.reference || "—"}</td>
                    <td className="text-center">
                      <button onClick={() => removeJuris(j.id)}
                        className="text-red-400 hover:text-red-300" data-testid={`del-juris-${j.id}`}>
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {tab === "banks" && (
        <div className="grid lg:grid-cols-3 gap-6 mt-6">
          <form onSubmit={addBank} className="vf-card p-6 space-y-3" data-testid="admin-add-bank">
            <div className="vf-serif text-xl text-slate-50 flex items-center gap-2">
              <Landmark className="w-5 h-5 text-[#D4AF37]" /> Ajouter un compte
            </div>
            <input required placeholder="Nom du titulaire" value={newBank.holder_name}
              onChange={(e) => setNewBank({ ...newBank, holder_name: e.target.value })}
              className="vf-input w-full px-3 py-2.5" data-testid="bank-holder" />
            <input required placeholder="Nom de la banque" value={newBank.bank_name}
              onChange={(e) => setNewBank({ ...newBank, bank_name: e.target.value })}
              className="vf-input w-full px-3 py-2.5" data-testid="bank-name" />
            <input required placeholder="IBAN" value={newBank.iban}
              onChange={(e) => setNewBank({ ...newBank, iban: e.target.value })}
              className="vf-input w-full px-3 py-2.5 vf-mono" data-testid="bank-iban" />
            <input placeholder="BIC / SWIFT" value={newBank.bic}
              onChange={(e) => setNewBank({ ...newBank, bic: e.target.value })}
              className="vf-input w-full px-3 py-2.5 vf-mono" data-testid="bank-bic" />
            <div className="grid grid-cols-2 gap-2">
              <select value={newBank.currency}
                onChange={(e) => setNewBank({ ...newBank, currency: e.target.value })}
                className="vf-input px-3 py-2.5">
                {["EUR","USD","GBP","CAD","CHF","AUD","MAD","TND","DZD"].map((c) =>
                  <option key={c}>{c}</option>)}
              </select>
              <input placeholder="Pays" value={newBank.country}
                onChange={(e) => setNewBank({ ...newBank, country: e.target.value })}
                className="vf-input px-3 py-2.5" />
            </div>
            <textarea rows={2} placeholder="Instructions complémentaires (facultatif)"
              value={newBank.instructions}
              onChange={(e) => setNewBank({ ...newBank, instructions: e.target.value })}
              className="vf-input w-full px-3 py-2.5 resize-y text-sm" />
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={newBank.is_active}
                onChange={(e) => setNewBank({ ...newBank, is_active: e.target.checked })}
                className="accent-[#D4AF37]" />
              Compte actif (proposé aux apprenants)
            </label>
            <button type="submit" className="vf-btn-primary w-full inline-flex items-center justify-center gap-2"
              data-testid="bank-add-submit">
              <Plus className="w-4 h-4" /> Ajouter le compte
            </button>
          </form>

          <div className="lg:col-span-2 vf-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[#0F1730] text-[#D4AF37]">
                <tr><th className="text-left p-3">Banque / Titulaire</th><th>IBAN</th><th>BIC</th>
                  <th>Devise</th><th>Actif</th><th></th></tr>
              </thead>
              <tbody>
                {bankAccounts.length === 0 && (
                  <tr><td colSpan={6} className="p-6 text-center text-slate-500">
                    Aucun compte bancaire enregistré.
                  </td></tr>
                )}
                {bankAccounts.map((b) => (
                  <tr key={b.id} className="border-t border-[#1E293B]" data-testid={`admin-bank-${b.id}`}>
                    <td className="p-3">
                      <div className="text-slate-100">{b.bank_name}</div>
                      <div className="text-xs text-slate-500">{b.holder_name}</div>
                    </td>
                    <td className="vf-mono text-xs text-slate-300">{b.iban}</td>
                    <td className="vf-mono text-xs text-slate-300">{b.bic || "—"}</td>
                    <td className="text-center text-slate-300">{b.currency}</td>
                    <td className="text-center">
                      <button onClick={() => toggleBankActive(b)}
                        data-testid={`bank-toggle-${b.id}`}
                        className={`text-xs px-2 py-1 border ${b.is_active
                          ? "border-emerald-500 text-emerald-400"
                          : "border-slate-600 text-slate-500"}`}>
                        {b.is_active ? "ACTIF" : "INACTIF"}
                      </button>
                    </td>
                    <td className="text-center">
                      <button onClick={() => removeBank(b.id)}
                        data-testid={`bank-del-${b.id}`}
                        className="text-red-400 hover:text-red-300">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "pending" && (
        <div className="vf-card mt-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-[#0F1730] text-[#D4AF37]">
              <tr><th className="text-left p-3">Référence VITA</th><th>Apprenant</th><th>Livrable</th>
                <th>Montant</th><th>Statut</th><th>Émetteur déclaré</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {pendingPayments.length === 0 && (
                <tr><td colSpan={7} className="p-6 text-center text-slate-500">
                  Aucun virement en attente.
                </td></tr>
              )}
              {pendingPayments.map((p) => (
                <tr key={p.id} className="border-t border-[#1E293B]" data-testid={`pending-${p.id}`}>
                  <td className="p-3 vf-mono text-xs text-[#D4AF37]">{p.wire_reference || "—"}</td>
                  <td className="text-slate-300 text-xs">{p.user_email}</td>
                  <td className="text-slate-200">{p.generation_topic}</td>
                  <td className="text-slate-100 vf-mono">
                    {p.amount?.toFixed(2)} {p.currency}
                  </td>
                  <td className="text-center text-xs">
                    {p.status === "wire_declared"
                      ? <span className="text-amber-300">DÉCLARÉ</span>
                      : <span className="text-slate-500">AWAITING</span>}
                  </td>
                  <td className="text-slate-300 text-xs">
                    {p.wire_sender_name || "—"}<br/>
                    <span className="text-slate-500">{p.wire_user_reference || ""}</span>
                  </td>
                  <td className="text-center">
                    <button onClick={() => validateWire(p.id)}
                      data-testid={`pending-validate-${p.id}`}
                      className="text-emerald-400 hover:text-emerald-300 mr-2">
                      <Check className="w-4 h-4" />
                    </button>
                    <button onClick={() => rejectWire(p.id)}
                      data-testid={`pending-reject-${p.id}`}
                      className="text-red-400 hover:text-red-300">
                      <X className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "revenue" && (
        <div className="space-y-6 mt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(revenue.by_currency).map(([cur, v]) => (
              <div key={cur} className="vf-card p-5" data-testid={`revenue-${cur}`}>
                <div className="vf-mono text-[0.65rem] tracking-[0.25em] text-[#D4AF37]/80">{cur}</div>
                <div className="vf-serif text-3xl text-slate-50 mt-2">
                  {cur === "JPY" ? v.total : v.total.toFixed(2)} <span className="text-base text-slate-400">{cur}</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">{v.count} paiement{v.count > 1 ? "s" : ""}</div>
              </div>
            ))}
            {Object.keys(revenue.by_currency).length === 0 && (
              <div className="vf-card p-8 col-span-full text-center text-slate-400">
                Aucune recette enregistrée pour le moment.
              </div>
            )}
          </div>

          <div className="vf-card p-6">
            <div className="vf-serif text-xl text-slate-50 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-[#D4AF37]" /> Détail mensuel
            </div>
            <div className="mt-4 space-y-4">
              {revenue.by_month.map((m) => (
                <div key={m.month}>
                  <div className="vf-mono text-xs text-[#D4AF37] mb-2">{m.month}</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                    {m.rows.map((r, i) => (
                      <div key={i} className="border border-[#1E293B] p-3 text-sm">
                        <div className="text-slate-200">
                          <span className="text-[#F3E5AB]">{r.method.toUpperCase()}</span> · {r.currency}
                        </div>
                        <div className="vf-serif text-xl text-slate-50">
                          {r.currency === "JPY" ? r.total : r.total.toFixed(2)}
                        </div>
                        <div className="text-xs text-slate-500">{r.count} paiement{r.count > 1 ? "s" : ""}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {revenue.by_month.length === 0 && (
                <p className="text-slate-500 text-sm">Aucune transaction confirmée pour l'instant.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {tab === "llm" && <LLMProvidersPanel />}
    </div>
  );
}
