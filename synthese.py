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
import geo
import search
import verifier
from noms import nom

ICI = Path(__file__).parent
FENETRE_JOURS = 30      # on garde les prix relevés pendant les 30 derniers jours
MAX_PAR_GROUPE = 40     # lignes gardées par destination et par catégorie
RATIO_MAX = 2.5         # on ignore les prix > 2,5 x le plafond de la zone
JOURS_DERNIERES = 7     # onglet « Dernières offres » : offres vues ces 7 derniers jours
MAX_DERNIERES = 300


def categorie(cfg, r):
    if r["type"] == "w":
        return "Week-end"
    if r["type"] == "v":
        return "Vacances (court séjour)"
    return "Long séjour · " + search.periode_de(cfg, r["_aller"])


def construire(today):
    lignes, recentes, meta_dest, records, cats = [], [], {}, {}, []
    verifs = verifier.lire_verifications()

    def ligne(cat, r, plaf):
        if cat not in cats:
            cats.append(cat)
        dest = r["destination"]
        continent, pays = geo.geo(dest)
        meta_dest.setdefault(dest, {"n": nom(dest), "k": continent, "p": pays})
        nuits = (r["_retour"] - r["_aller"]).days
        total = r["prix"]
        h = couts.hotel_nuit(dest, r["_aller"].month)
        if h:
            total += h * nuits
        if r["type"] != "l" and dest in couts.TRANSFERT:
            total += couts.TRANSFERT[dest][1]
        return [cats.index(cat), r["depart"], dest, r["aller"], r["retour"], r["prix"],
                r["releve"], r["compagnie"], round(total), plaf,
                r.get("_ancien", 0), r.get("_note", ""), r.get("_verif", "")]

    for dossier, _, fichier in bilan.SOURCES:
        cfg = yaml.safe_load((ICI / fichier).read_text(encoding="utf-8"))
        rows = bilan.lire(ICI / "data" / dossier)
        meilleurs = {}
        for r in rows:
            cat = categorie(cfg, r)
            # les records tiennent compte de TOUT l'historique, y compris des vols déjà passés
            rk = f"{r['destination']}|{r['depart']}|{cat}"
            if rk not in records or r["prix"] < records[rk][0]:
                records[rk] = [r["prix"], r["releve"]]
            # mais la page n'affiche que des vols à venir, relevés récemment
            if (today - r["_rel"]).days > FENETRE_JOURS or r["_aller"] <= today:
                continue
            ck = (cat, r["depart"], r["destination"], r["aller"], r["retour"])
            meilleurs[ck] = r   # relevés dans l'ordre chronologique : le plus récent l'emporte (prix actuel)
        # revérifications (verifier.py) : plus récentes que le relevé -> elles corrigent le prix affiché
        for ck, r in list(meilleurs.items()):
            v = verifs.get((r["type"], r["depart"], r["destination"], r["aller"], r["retour"]))
            if not v or v["verifie"] < r["releve"]:
                continue
            r = dict(r)
            r["_verif"] = v["verifie"]
            if v["statut"] == "introuvable":
                if v["introuvable_n"] >= 2:
                    del meilleurs[ck]       # introuvable deux fois de suite : masquée
                    continue
                r["_note"] = "d"            # doute : à revérifier
            else:
                if v["apres"] != v["avant"]:
                    r["_ancien"] = v["avant"]
                r["prix"] = v["apres"]
                r["_note"] = {"baisse": "b", "hausse": "h"}.get(v["statut"], "o")
                if v["statut"] == "baisse":  # une baisse = une nouvelle offre : elle remonte en tête
                    r["releve"] = v["verifie"]
                    r["_rel"] = date.fromisoformat(v["verifie"])
            meilleurs[ck] = r
        groupes, derniers = {}, {}
        for ck, r in meilleurs.items():
            plaf, _ = search.plafond(cfg, bilan.KIND[r["type"]], r["destination"])
            if plaf and r["prix"] > plaf * RATIO_MAX:
                continue
            groupes.setdefault((ck[0], r["destination"]), []).append((r, plaf))
            # onglet « Dernières offres » : offres sous le plafond vues ces 7 derniers jours,
            # la moins chère par destination, départ et catégorie
            if plaf and r["prix"] <= plaf and (today - r["_rel"]).days <= JOURS_DERNIERES:
                k2 = (ck[0], r["depart"], r["destination"])
                if k2 not in derniers or r["prix"] < derniers[k2][0]["prix"]:
                    derniers[k2] = (r, plaf)
        for (cat, dest), lst in groupes.items():
            lst.sort(key=lambda x: x[0]["prix"])
            for r, plaf in lst[:MAX_PAR_GROUPE]:
                lignes.append(ligne(cat, r, plaf))
        for (cat, _, _), (r, plaf) in derniers.items():
            recentes.append(ligne(cat, r, plaf))
    recentes.sort(key=lambda x: (x[6], -x[5]), reverse=True)   # les plus récemment vus d'abord
    depart_noms = {l[1]: nom(l[1]) for l in lignes + recentes}
    return {"cats": cats, "dests": meta_dest, "departs": depart_noms, "rows": lignes,
            "recent": recentes[:MAX_DERNIERES], "records": records, "genere": today.isoformat()}


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
details.c{padding:0}details.c>summary{list-style:none;cursor:pointer;padding:11px 13px}
details.c>summary::-webkit-details-marker{display:none}
.plus{color:var(--acc);font-size:.9rem;margin-top:6px;font-weight:600}
details[open] .plus::after{content:" (replier)"}
.sub{border-top:1px solid var(--line);padding:8px 13px;display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.sub .px{font-size:1.05rem}
.tabs{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.tabs button{padding:11px;font:inherit;font-weight:600;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);cursor:pointer}
.tabs button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.jour{font-weight:700;margin:14px 0 2px}
</style></head><body><main>
<h1>✈️ Offres de vols</h1>
<div class="tabs"><button id="b1" class="on">🔎 Recherche</button><button id="b2">🆕 Dernières offres</button></div>
<div id="v2" hidden>
 <div class="ctl"><div class="row"><select id="rtype"><option value="">Tous les types</option><option value="Week-end">Week-ends</option><option value="Vacances">Vacances (court séjour)</option><option value="Long">Longs séjours</option></select>
 <select id="rfra"><option value="1">Vues depuis 24 h</option><option value="3">Vues depuis 3 jours</option><option value="7" selected>Vues depuis 7 jours</option></select></div></div>
 <div class="info" id="info2"></div><div id="out2"></div>
</div>
<div id="v1">
<div class="ctl">
 <input id="q" type="search" placeholder="Destination (ex. Prague, Bakou, BKK…)" autocomplete="off" list="dl">
 <datalist id="dl"></datalist>
 <div class="row"><select id="cat"></select><select id="dep"></select></div>
 <div class="row"><select id="kont"></select><select id="pays"></select></div>
 <div class="row"><select id="fra"><option value="999">Vus à n'importe quel moment</option><option value="1">Nouveautés : vus depuis 24 h</option><option value="3">Vus depuis 3 jours</option><option value="7">Vus depuis 7 jours</option></select>
 <select id="ok"><option value="0">Tous les prix</option><option value="1">Seulement sous le plafond</option></select></div>
 <div class="row"><select id="tri"><option value="p">Du moins cher au plus cher</option><option value="d">Par date de départ</option><option value="t">Par coût total estimé</option><option value="n">Les plus récemment vus</option></select><div></div></div>
</div>
<div class="info" id="info"></div><div id="out"></div>
</div>
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
$("cat").innerHTML='<option value="-1">Toutes les dates (tous types)</option>'+D.cats.map((c,i)=>`<option value="${i}">${c}</option>`).join("");
// un vol dont la date de départ est passée disparaît de la page (il reste dans la base pour les comparaisons)
const AUJ=new Date().toLocaleDateString("sv-SE");
const futur=x=>x[3]>AUJ;
$("dep").innerHTML='<option value="">Tous les départs</option>'+Object.entries(D.departs).sort((a,b)=>a[1].localeCompare(b[1])).map(([k,v])=>`<option value="${k}">${v}</option>`).join("");
$("dl").innerHTML=Object.entries(D.dests).map(([k,v])=>`<option value="${v.n}">`).join("");
const konts=[...new Set(Object.values(D.dests).map(v=>v.k))].sort();
$("kont").innerHTML='<option value="">Tous les continents</option>'+konts.map(k=>`<option>${k}</option>`).join("");
function paysList(){
  const k=$("kont").value;
  const ps=[...new Set(Object.values(D.dests).filter(v=>!k||v.k===k).map(v=>v.p))].sort();
  $("pays").innerHTML='<option value="">Tous les pays</option>'+ps.map(p=>`<option>${p}</option>`).join("");
}
paysList();
$("foot").textContent="Données du journal d'observations ("+D.genere.split("-").reverse().join("/")+"). Prix vus par Google Flights au moment du relevé : à revérifier avant de réserver. Séjour estimé = vol + hôtel + transferts (estimations).";
const age=s=>Math.round((new Date(D.genere)-new Date(s))/864e5);   // jours depuis le relevé
const neuf=s=>age(s)<=1?'<span class="ok">🆕 </span>':"";
const SEUIL=3;   // au-delà de 3 offres pour une même destination, on les regroupe dans un bloc
// lien Google Flights pré-rempli (aéroports, dates, aller-retour, euros) : même construction que le script
const vi=n=>{const o=[];do{let b=n&127;n>>>=7;if(n)b|=128;o.push(b)}while(n);return o};
const ch=(num,pl)=>[...vi((num<<3)|2),...vi(pl.length),...pl];
const enc=s=>[...new TextEncoder().encode(s)];
const aero=c=>[8,1,...ch(2,enc(c))];
const vol=(j,d,a,dir)=>[...ch(2,enc(j)),...(dir?[0x28,0]:[]),...ch(13,aero(d)),...ch(14,aero(a))];
function tfs(o,dest,a,b,dir){
  const x=[8,0x1c,0x10,2,...ch(3,vol(a,o,dest,dir)),...ch(3,vol(b,dest,o,dir)),0x40,1,0x48,1,0x70,1,...ch(16,[8,...Array(9).fill(255),1]),0x98,1,1];
  return btoa(String.fromCharCode(...x)).replace(/\\+/g,"-").replace(/\\//g,"_").replace(/=+$/,"");
}
function lien(o,dest,a,b,cat){
  const direct=!D.cats[cat].startsWith("Long");   // court courrier : vols directs seulement
  return `https://www.google.com/travel/flights/search?tfs=${tfs(o,dest,a,b,direct)}&hl=fr&curr=EUR`;
}
function flag(p,plaf){return p<=plaf?`<span class="ok">✅ sous le plafond (${plaf} €)</span>`:(plaf?`<span class="warn">${Math.round((p/plaf-1)*100)} % au-dessus du plafond (${plaf} €)</span>`:"")}
function note(x){
  const [,, , , ,p, , , , ,ancien,etat,verif]=x;
  if(etat==="b")return `<div class="m ok">📉 Baissé de ${ancien} € à ${p} € (vérifié le ${fd(verif)})</div>`;
  if(etat==="h")return `<div class="m warn">📈 Monté de ${ancien} € à ${p} € (vérifié le ${fd(verif)})</div>`;
  if(etat==="o")return `<div class="m">✔️ Prix confirmé le ${fd(verif)}</div>`;
  if(etat==="d")return `<div class="m warn">⚠️ Introuvable à la dernière vérification (${fd(verif)}) : à revérifier</div>`;
  return "";
}
function card(x){
  const [cat,o,dest,a,b,p,seen,cie,tot,plaf]=x,rec=D.records[dest+"|"+o+"|"+D.cats[cat]];
  const recl=rec?`Record : ${rec[0]} € (vu le ${fd(rec[1])})`+(p<=rec[0]?" · 🏆 égale/bat le record":""):"";
  return `<div class="top"><div><div class="d">${neuf(seen)}${D.departs[o]} ⇄ ${D.dests[dest].n}</div><div>${fj(a)} → ${fj(b)} · ${nuits(a,b)} nuits · <span class="m">${D.cats[cat]}</span></div></div><div class="px ${p<=plaf?"ok":""}">${p} €</div></div>
  <div class="m">${flag(p,plaf)}</div>${note(x)}<div class="m">${recl}</div>
  <div class="m">Séjour estimé ≈ ${tot} € · ${cie||"compagnie inconnue"} · vu le ${fd(seen)} · <a href="${lien(o,dest,a,b,cat)}" target="_blank" rel="noopener">Google Flights</a></div>`;
}
function sub(x){
  const [cat,o,dest,a,b,p,seen,cie,tot,plaf]=x;
  return `<div class="sub"><div><div>${fj(a)} → ${fj(b)} · ${nuits(a,b)} nuits <span class="m">· ${D.cats[cat]}</span></div><div class="m">${D.departs[o]} · ${flag(p,plaf)} ${x[11]==="b"?"· 📉 baissé de "+x[10]+" €":x[11]==="h"?"· 📈 monté de "+x[10]+" €":x[11]==="d"?"· ⚠️ à revérifier":""} · ≈ ${tot} € tout compris · ${cie||"?"} · vu le ${fd(seen)} · <a href="${lien(o,dest,a,b,cat)}" target="_blank" rel="noopener">Google Flights</a></div></div><div class="px ${p<=plaf?"ok":""}">${p} €</div></div>`;
}
function render(){
  const q=norm($("q").value.trim()),cat=+$("cat").value,dep=$("dep").value,tri=$("tri").value,seul=$("ok").value==="1",k=$("kont").value,pa=$("pays").value;
  let r=D.rows.filter(x=>futur(x)&&(cat<0||x[0]===cat)&&(!dep||x[1]===dep));
  if(k)r=r.filter(x=>D.dests[x[2]].k===k);
  if(pa)r=r.filter(x=>D.dests[x[2]].p===pa);
  if(q)r=r.filter(x=>norm(D.dests[x[2]].n).includes(q)||norm(x[2]).includes(q)||norm(D.dests[x[2]].p).includes(q));
  if(seul)r=r.filter(x=>x[9]&&x[5]<=x[9]);
  const fra=+$("fra").value;if(fra<999)r=r.filter(x=>age(x[6])<=fra);
  r.sort((a,b)=>tri==="d"?a[3].localeCompare(b[3])||a[5]-b[5]:tri==="t"?a[8]-b[8]:tri==="n"?b[6].localeCompare(a[6])||a[5]-b[5]:a[5]-b[5]);
  const g=new Map();                       // destination -> offres, dans l'ordre du tri
  r.forEach(x=>{if(!g.has(x[2]))g.set(x[2],[]);g.get(x[2]).push(x)});
  const groupes=[...g.values()];
  $("info").textContent=r.length?`${groupes.length} destination(s), ${r.length} offre(s)`+(groupes.length>50?" (50 premières affichées, filtre par pays ou continent)":""):"Aucune offre pour ces critères.";
  $("out").innerHTML=groupes.slice(0,50).map(l=>{
    if(l.length<=SEUIL)return l.map(x=>`<div class="c">${card(x)}</div>`).join("");
    const n=l.length-1;
    return `<details class="c"><summary>${card(l[0])}<div class="plus">+ ${n} autre${n>1?"s":""} date${n>1?"s":""} pour ${D.dests[l[0][2]].n}</div></summary>${l.slice(1,61).map(sub).join("")}${l.length>61?`<div class="sub m">… et ${l.length-61} autres (précise les filtres)</div>`:""}</details>`;
  }).join("");
}
function renderRecent(){
  const t=$("rtype").value,fra=+$("rfra").value;
  const r=D.recent.filter(x=>futur(x)&&age(x[6])<=fra&&(!t||D.cats[x[0]].startsWith(t)));
  $("info2").textContent=r.length?`${r.length} offre(s) sous le plafond, des plus récentes aux plus anciennes`:"Aucune offre récente sous le plafond pour ces critères.";
  let h="",dernier="";
  r.slice(0,100).forEach(x=>{
    const j=age(x[6]),lab=j<=0?"Aujourd'hui":j===1?"Hier":`Il y a ${j} jours (${fd(x[6])})`;
    if(lab!==dernier){h+=`<div class="jour">${lab}</div>`;dernier=lab}
    h+=`<div class="c">${card(x)}</div>`;
  });
  $("out2").innerHTML=h;
}
function onglet(n){
  $("v1").hidden=n!==1;$("v2").hidden=n!==2;
  $("b1").classList.toggle("on",n===1);$("b2").classList.toggle("on",n===2);
  if(n===2)renderRecent();
}
$("b1").onclick=()=>onglet(1);$("b2").onclick=()=>onglet(2);
["rtype","rfra"].forEach(i=>$(i).addEventListener("input",renderRecent));
$("kont").addEventListener("input",()=>{paysList();render()});
["q","cat","dep","tri","ok","pays","fra"].forEach(i=>$(i).addEventListener("input",render));
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
