#!/usr/bin/env python3
"""Page de recherche des offres : data/synthese/index.html

Tape une destination, choisis week-end ou vacances (ou long séjour), et la page liste les dates
avec leurs prix, du moins cher au plus cher, avec le plafond, le record et le séjour estimé.
Elle est reconstruite deux fois par jour à partir du journal d'observations (workflow synthese.yml)."""
import json
from datetime import date, timedelta
from pathlib import Path

import yaml

import bilan
import couts
import search
from noms import nom

ICI = Path(__file__).parent
FENETRE_JOURS = 30      # on garde les prix relevés pendant les 30 derniers jours
MAX_PAR_GROUPE = 40     # lignes gardées par destination et par catégorie
RATIO_MAX = 2.5         # on ignore les prix > 2,5 x le plafond de la zone


def categorie(cfg, r):
    if r["type"] == "w":
        return "Week-end"
    if r["type"] == "v":
        return "Vacances (court séjour)"
    return "Long séjour · " + search.periode_de(cfg, r["_aller"])


def construire(today):
    lignes, meta_dest, records, cats = [], {}, {}, []
    for dossier, _, fichier in bilan.SOURCES:
        cfg = yaml.safe_load((ICI / fichier).read_text(encoding="utf-8"))
        rows = bilan.lire(ICI / "data" / dossier)
        meilleurs = {}
        for r in rows:
            cat = categorie(cfg, r)
            rk = f"{r['destination']}|{r['depart']}|{cat}"
            if rk not in records or r["prix"] < records[rk][0]:
                records[rk] = [r["prix"], r["releve"]]
            if (today - r["_rel"]).days > FENETRE_JOURS or r["_aller"] <= today:
                continue
            ck = (cat, r["depart"], r["destination"], r["aller"], r["retour"])
            if ck not in meilleurs or r["prix"] < meilleurs[ck]["prix"]:
                meilleurs[ck] = r
        groupes = {}
        for ck, r in meilleurs.items():
            plaf, _ = search.plafond(cfg, bilan.KIND[r["type"]], r["destination"])
            if plaf and r["prix"] > plaf * RATIO_MAX:
                continue
            groupes.setdefault((ck[0], r["destination"]), []).append((r, plaf))
        for (cat, dest), lst in groupes.items():
            if cat not in cats:
                cats.append(cat)
            meta_dest.setdefault(dest, {"n": nom(dest)})
            lst.sort(key=lambda x: x[0]["prix"])
            for r, plaf in lst[:MAX_PAR_GROUPE]:
                nuits = (r["_retour"] - r["_aller"]).days
                total = r["prix"]
                h = couts.hotel_nuit(dest, r["_aller"].month)
                if h:
                    total += h * nuits
                if r["type"] != "l" and dest in couts.TRANSFERT:
                    total += couts.TRANSFERT[dest][1]
                lignes.append([cats.index(cat), r["depart"], dest, r["aller"], r["retour"], r["prix"],
                               r["releve"], r["compagnie"], round(total), plaf])
    depart_noms = {l[1]: nom(l[1]) for l in lignes}
    recs = {k: v for k, v in records.items()}
    return {"cats": cats, "dests": meta_dest, "departs": depart_noms, "rows": lignes,
            "records": recs, "genere": today.isoformat()}


PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Offres de vols</title>
<style>
:root{--bg:#fff;--fg:#1b1f24;--mut:#6b7280;--card:#f4f6f8;--ok:#0a7d3b;--warn:#b45309;--line:#d9dee3;--acc:#1a56db}
@media (prefers-color-scheme:dark){:root{--bg:#14171a;--fg:#e8eaed;--mut:#9aa3ad;--card:#1f2428;--ok:#4ade80;--warn:#fbbf24;--line:#2d343a;--acc:#7aa7ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.4 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:16px}
h1{font-size:1.3rem;margin:0 0 12px}
.ctl{display:grid;gap:8px;margin-bottom:12px}
input,select{width:100%;padding:11px;font:inherit;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.c{background:var(--card);border-radius:10px;padding:11px 13px;margin:8px 0}
.top{display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.px{font-size:1.25rem;font-weight:700}.ok{color:var(--ok)}.warn{color:var(--warn)}
.m{color:var(--mut);font-size:.85rem}.d{font-weight:600}
a{color:var(--acc)}
.info{color:var(--mut);font-size:.85rem;margin:6px 0}
</style></head><body><main>
<h1>✈️ Offres de vols</h1>
<div class="ctl">
 <input id="q" type="search" placeholder="Destination (ex. Prague, Bakou, BKK…)" autocomplete="off" list="dl">
 <datalist id="dl"></datalist>
 <div class="row"><select id="cat"></select><select id="dep"></select></div>
 <div class="row"><select id="tri"><option value="p">Du moins cher au plus cher</option><option value="d">Par date de départ</option><option value="t">Par coût total estimé</option></select>
 <select id="ok"><option value="0">Tous les prix</option><option value="1">Seulement sous le plafond</option></select></div>
</div>
<div class="info" id="info"></div><div id="out"></div>
<p class="m" id="foot"></p>
</main>
<script>
const D=__DATA__;
const $=id=>document.getElementById(id);
const norm=s=>s.normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase();
const fd=s=>{const[a,b,c]=s.split("-");return c+"/"+b};
const jours=["dim","lun","mar","mer","jeu","ven","sam"];
const fj=s=>jours[new Date(s+"T12:00:00").getDay()]+" "+fd(s);
const nuits=(a,b)=>Math.round((new Date(b)-new Date(a))/864e5);
$("cat").innerHTML=D.cats.map((c,i)=>`<option value="${i}">${c}</option>`).join("");
$("dep").innerHTML='<option value="">Tous les départs</option>'+Object.entries(D.departs).sort((a,b)=>a[1].localeCompare(b[1])).map(([k,v])=>`<option value="${k}">${v}</option>`).join("");
$("dl").innerHTML=Object.entries(D.dests).map(([k,v])=>`<option value="${v.n}">`).join("");
$("foot").textContent="Données du journal d'observations ("+D.genere.split("-").reverse().join("/")+"). Prix vus par Google Flights au moment du relevé : à revérifier avant de réserver. Séjour estimé = vol + hôtel + transferts (estimations).";
function render(){
  const q=norm($("q").value.trim()),cat=+$("cat").value,dep=$("dep").value,tri=$("tri").value,seul=$("ok").value==="1";
  let r=D.rows.filter(x=>x[0]===cat&&(!dep||x[1]===dep));
  if(q)r=r.filter(x=>norm(D.dests[x[2]].n).includes(q)||norm(x[2]).includes(q));
  if(seul)r=r.filter(x=>x[9]&&x[5]<=x[9]);
  r.sort((a,b)=>tri==="d"?a[3].localeCompare(b[3])||a[5]-b[5]:tri==="t"?a[8]-b[8]:a[5]-b[5]);
  const n=r.length;r=r.slice(0,60);
  $("info").textContent=n?n+" offre(s)"+(n>60?" (60 affichées, précise la destination)":""):"Aucune offre pour ces critères.";
  $("out").innerHTML=r.map(x=>{
    const [,o,dest,a,b,p,seen,cie,tot,plaf]=x,N=D.dests[dest].n,rec=D.records[dest+"|"+o+"|"+D.cats[cat]];
    const sous=plaf&&p<=plaf,rapport=plaf?(p/plaf):0;
    const lien="https://www.google.com/travel/flights?hl=fr&curr=EUR&q="+encodeURIComponent(`Flights from ${o} to ${dest} on ${a} through ${b}`);
    const flag=sous?`<span class="ok">✅ sous le plafond (${plaf} €)</span>`:(plaf?`<span class="warn">${Math.round((rapport-1)*100)} % au-dessus du plafond (${plaf} €)</span>`:"");
    const recl=rec?`Record : ${rec[0]} € (vu le ${fd(rec[1])})`+(p<=rec[0]?" · 🏆 égale/bat le record":""):"";
    return `<div class="c"><div class="top"><div><div class="d">${D.departs[o]} ⇄ ${N}</div><div>${fj(a)} → ${fj(b)} · ${nuits(a,b)} nuits</div></div><div class="px ${sous?"ok":""}">${p} €</div></div>
    <div class="m">${flag}</div><div class="m">${recl}</div>
    <div class="m">Séjour estimé ≈ ${tot} € · ${cie||"compagnie inconnue"} · vu le ${fd(seen)} · <a href="${lien}" target="_blank" rel="noopener">Google Flights</a></div></div>`}).join("");
}
["q","cat","dep","tri","ok"].forEach(i=>$(i).addEventListener("input",render));
render();
</script></body></html>
"""


def main():
    today = date.today()
    data = construire(today)
    sortie = ICI / "data" / "synthese"
    sortie.mkdir(parents=True, exist_ok=True)
    if not data["cats"]:   # pas encore de données : la page reste utilisable
        data["cats"] = ["Aucune donnée pour l'instant"]
    html = PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    (sortie / "index.html").write_text(html, encoding="utf-8")
    print(f"Page écrite : {len(data['rows'])} offres, {len(html) // 1024} Ko")


if __name__ == "__main__":
    main()
