import { Linkedin, BookOpen, ExternalLink, GraduationCap, Scale } from "lucide-react";

export default function Auteur() {
  return (
    <div className="max-w-6xl mx-auto px-6 md:px-12 py-16">
      <div className="grid lg:grid-cols-12 gap-12 items-start">
        <div className="lg:col-span-5">
          <div className="vf-frame bg-[#0F1730]/60">
            <img
              src="https://customer-assets.emergentagent.com/job_4b295bcf-9dab-41b7-9ef2-697a4cc68804/artifacts/wrvl79bo_past-forward-1950s%20%283%29.jpg"
              alt="Pr. Ahmed ELY Mustapha"
              className="w-full grayscale-[0.15] border border-[#D4AF37]/30"
              data-testid="author-photo"
            />
          </div>
          <div className="mt-8 space-y-3">
            <a
              href="https://www.linkedin.com/in/mustapha-ahmed-ely-06041959"
              target="_blank" rel="noreferrer"
              data-testid="linkedin-blue"
              className="flex items-center gap-3 px-5 py-3 border border-[#0A66C2] text-[#0A66C2] hover:bg-[#0A66C2]/10 transition-colors"
            >
              <Linkedin className="w-5 h-5" />
              <span className="text-sm">LinkedIn — Consultant international en droit public (chaîne pénale)</span>
              <ExternalLink className="w-3.5 h-3.5 ml-auto" />
            </a>
            <a
              href="https://www.linkedin.com/in/mustapha-ahmed-ely-843640248"
              target="_blank" rel="noreferrer"
              data-testid="linkedin-green"
              className="flex items-center gap-3 px-5 py-3 border border-[#057642] text-[#057642] hover:bg-[#057642]/10 transition-colors"
            >
              <Linkedin className="w-5 h-5" />
              <span className="text-sm">LinkedIn — Professeur d'université en Finances publiques</span>
              <ExternalLink className="w-3.5 h-3.5 ml-auto" />
            </a>
          </div>
        </div>

        <div className="lg:col-span-7 vf-fade-up">
          <span className="vf-tag" data-testid="auteur-tag">L'auteur</span>
          <h1 className="vf-serif text-4xl sm:text-5xl mt-4 text-slate-50">
            Pr. Ahmed ELY Mustapha
          </h1>
          <p className="text-[#D4AF37] mt-2 italic">Docteur d'État en Droit public et Finances publiques</p>

          <div className="mt-7 space-y-4 text-slate-300 leading-relaxed">
            <p>
              Professeur d'Université, consultant international en droit public — spécialiste de la chaîne pénale —
              et chercheur pluridisciplinaire, le Professeur Ahmed ELY Mustapha est l'auteur d'une trentaine d'ouvrages
              et essais publiés. Certifications : <strong className="text-[#F3E5AB]">PMP, I-PMP, SSYB, CSP, CEH</strong>.
            </p>
            <p>
              Sa <strong className="text-[#F3E5AB]">Théorie Vitaliste des Finances Publiques</strong> opère une rupture
              épistémologique avec un siècle de doctrine classique en restituant aux deniers de l'État leur dimension
              première : du temps de vie humaine traduit en monnaie. Influencée par Bachelard, Rawls, Sartre et la
              relativité einsteinienne, elle élève le service public au rang de mission sacrée et fonde une éthique
              de la vie collective.
            </p>
          </div>

          <div className="mt-10">
            <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">BIBLIOGRAPHIE — OUVRAGES PHARES</div>
            <div className="grid sm:grid-cols-2 gap-4 mt-5">
              <a
                href="https://www.amazon.fr/s?k=Ahmed+ELY+Mustapha+Finances+publiques+nouvelle+théorie"
                target="_blank" rel="noreferrer"
                data-testid="bibli-finances"
                className="vf-card p-6 group"
              >
                <BookOpen className="w-6 h-6 text-[#D4AF37]" />
                <div className="vf-serif text-lg mt-3 text-slate-50 leading-snug">
                  Finances publiques.<br/>Une nouvelle Théorie.
                </div>
                <div className="text-xs text-slate-400 mt-2">Voir sur Amazon ↗</div>
              </a>
              <a
                href="https://www.amazon.fr/s?k=Ahmed+ELY+Mustapha+manuel+pouvoir"
                target="_blank" rel="noreferrer"
                data-testid="bibli-pouvoir"
                className="vf-card p-6 group"
              >
                <BookOpen className="w-6 h-6 text-[#D4AF37]" />
                <div className="vf-serif text-lg mt-3 text-slate-50 leading-snug">
                  Manuel à l'usage de ceux qui veulent prendre le pouvoir… et y rester.
                </div>
                <div className="text-xs text-slate-400 mt-2">Voir sur Amazon ↗</div>
              </a>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4 mt-10">
            <div className="vf-card p-6">
              <Scale className="w-6 h-6 text-[#D4AF37]" />
              <div className="vf-serif text-lg mt-3 text-slate-50">Droit public & pénal</div>
              <p className="text-sm text-slate-400 mt-2">Consultations internationales, chaîne pénale, gouvernance.</p>
            </div>
            <div className="vf-card p-6">
              <GraduationCap className="w-6 h-6 text-[#D4AF37]" />
              <div className="vf-serif text-lg mt-3 text-slate-50">Enseignement universitaire</div>
              <p className="text-sm text-slate-400 mt-2">Finances publiques, théorie générale, doctorat.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
