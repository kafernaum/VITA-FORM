import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Crown, Trash2, Plus, Users2, FileSignature, BadgeDollarSign, Building2 } from "lucide-react";

export default function Admin() {
  const [tab, setTab] = useState("users");
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [generations, setGenerations] = useState([]);
  const [institutions, setInstitutions] = useState([]);
  const [jurisprudences, setJurisprudences] = useState([]);
  const [newInst, setNewInst] = useState({ name: "", country: "France", country_code: "FR", city: "", type: "ENA" });
  const [newJur, setNewJur] = useState({ title: "", country: "France", reference: "", body: "", tags: "" });

  const refresh = () => {
    api.get("/admin/stats").then((r) => setStats(r.data));
    api.get("/admin/users").then((r) => setUsers(r.data));
    api.get("/admin/generations").then((r) => setGenerations(r.data));
    api.get("/institutions").then((r) => setInstitutions(r.data));
    api.get("/jurisprudences", { params: { limit: 100 } }).then((r) => setJurisprudences(r.data));
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
    </div>
  );
}
