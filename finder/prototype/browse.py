"""Score every offer and write offers.html -- a self-contained, clickable review page.

    python browse.py            # writes offers.html next to this script, opens nothing
    python browse.py --open     # writes it and opens it in the browser

The page shows a  category x bucket  grid. Click any cell to see exactly the offers that
landed there. Edit keywords.py, re-run this, refresh the tab.
"""
import json, os, sys, webbrowser, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scoring import classify, BUCKETS

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "data", "offers_db.jsonl")
OUT = os.path.join(HERE, "offers.html")

def main():
    rows = [json.loads(l) for l in open(DB, encoding="utf-8")]
    offers = []
    for o in rows:
        b, score, why = classify(o)
        url = ""
        for s in o.get("sources", []):
            if s.get("url"):
                url = s["url"]; break
        offers.append([
            score,                              # 0
            BUCKETS.index(b),                   # 1  bucket index 0..5
            o.get("category", "?"),             # 2
            o["title"],                         # 3
            o.get("company", ""),               # 4
            ", ".join(o["skills"]),             # 5
            why,                                # 6
            url,                                # 7
            ", ".join(o.get("cities", [])),     # 8
            o.get("level", ""),                 # 9
            o.get("workplace", ""),             # 10
            o.get("salary", ""),                # 11
        ])
    payload = json.dumps({"buckets": BUCKETS, "offers": offers}, ensure_ascii=False)
    html = TEMPLATE.replace("/*DATA*/", payload)
    open(OUT, "w", encoding="utf-8").write(html)

    tab = collections.Counter((BUCKETS[o[1]], o[2]) for o in offers)
    print(f"{len(offers)} offers -> {OUT}")
    for b in BUCKETS:
        print(f"  {b:9} {sum(v for (bb, _), v in tab.items() if bb == b):5}")
    if "--open" in sys.argv:
        webbrowser.open("file:///" + OUT.replace("\\", "/"))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Offer triage — category × bucket</title>
<style>
  :root{
    --bg:#0f1115; --fg:#e6e6e6; --dim:#9aa0aa; --line:#262a33; --card:#161a21;
    --b1:#7a1f1f; --b2:#8a3b1f; --b3:#3a3f49; --b4:#7a6a1f; --b5:#3f6a2f; --b6:#1f7a3f;
  }
  @media (prefers-color-scheme:light){
    :root{--bg:#f6f7f9;--fg:#1b1e24;--dim:#5c636e;--line:#dde1e7;--card:#fff;
      --b1:#e7b3b3;--b2:#eac6ad;--b3:#d8dbe0;--b4:#e6dca8;--b5:#c3e0b3;--b6:#a8e0bd;}
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);
    font:14px/1.45 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
  header{padding:14px 18px;border-bottom:1px solid var(--line)}
  h1{font-size:16px;margin:0 0 3px} .sub{color:var(--dim);font-size:12px}
  .wrap{padding:14px 18px}
  table.grid{border-collapse:collapse;font-size:12px}
  table.grid th,table.grid td{border:1px solid var(--line);padding:4px 7px;text-align:center;
    cursor:pointer;white-space:nowrap;user-select:none}
  table.grid th{color:var(--dim);font-weight:600;background:var(--card)}
  table.grid td.cat{text-align:left;color:var(--fg);font-weight:600;background:var(--card)}
  table.grid td.n{font-variant-numeric:tabular-nums;min-width:52px}
  table.grid td.z{color:var(--dim);opacity:.35}
  td.b0{background:var(--b1)}td.b1{background:var(--b2)}td.b2{background:var(--b3)}
  td.b3{background:var(--b4)}td.b4{background:var(--b5)}td.b5{background:var(--b6)}
  tr.tot td,td.tot{font-weight:700;background:var(--card)}
  .sel{outline:3px solid #4a9eff;outline-offset:-3px}
  .hint{color:var(--dim);font-size:12px;margin:10px 0 4px}
  .bar{display:flex;gap:10px;align-items:center;margin:12px 0 4px;flex-wrap:wrap}
  input[type=search]{background:var(--card);border:1px solid var(--line);color:var(--fg);
    padding:6px 10px;border-radius:6px;min-width:240px;font-size:13px}
  .cnt{color:var(--dim);font-size:12px}
  ul.offers{list-style:none;margin:8px 0;padding:0}
  li.of{border:1px solid var(--line);border-left-width:4px;border-radius:7px;
    padding:8px 11px;margin:7px 0;background:var(--card)}
  li.of .top{display:flex;gap:9px;align-items:baseline;flex-wrap:wrap}
  .num{color:var(--dim);font-variant-numeric:tabular-nums;min-width:34px;text-align:right;
    font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
  .score{font-weight:700;font-variant-numeric:tabular-nums;min-width:34px}
  .ttl{font-weight:600}
  a.ttl{color:inherit;text-decoration:none;border-bottom:1px dotted var(--dim)}
  a.ttl:hover{border-bottom-style:solid}
  .co{color:var(--dim)} .badge{font-size:11px;color:var(--dim);border:1px solid var(--line);
    border-radius:10px;padding:0 7px}
  .sk{color:var(--dim);font-size:12px;margin-top:3px}
  .applybtn{margin-left:auto;background:var(--card);border:1px solid var(--line);
    color:var(--dim);border-radius:6px;padding:3px 9px;font-size:12px;cursor:pointer;
    white-space:nowrap}
  .applybtn:hover{border-color:#4a9eff;color:var(--fg)}
  li.of.applied{opacity:.5}
  li.of.applied .ttl{text-decoration:line-through}
  li.of.applied .applybtn{background:#1f7a3f;border-color:#1f7a3f;color:#fff;opacity:1}
  label.chk{color:var(--dim);font-size:12px;display:flex;align-items:center;gap:5px;cursor:pointer}
  button.tool{background:var(--card);border:1px solid var(--line);color:var(--fg);
    padding:6px 10px;border-radius:6px;font-size:12px;cursor:pointer}
  button.tool:hover{border-color:#4a9eff}
  .why{font-size:11.5px;margin-top:3px;font-family:ui-monospace,Menlo,Consolas,monospace}
  .pos{color:#3fae5f}.neg{color:#e06a6a}
  .lb0{border-left-color:var(--b1)}.lb1{border-left-color:var(--b2)}.lb2{border-left-color:var(--b3)}
  .lb3{border-left-color:var(--b4)}.lb4{border-left-color:var(--b5)}.lb5{border-left-color:var(--b6)}
</style></head><body>
<header>
  <h1>Offer triage — category × bucket</h1>
  <div class="sub">Click any cell to see its offers. Click a row or column label for the whole
    row / column. Buckets left→right: KILL · VETO · NEG · WEAK · PLAUSIBLE · STRONG.</div>
</header>
<div class="wrap">
  <div id="grid"></div>
  <div class="bar">
    <strong id="selname">All offers</strong>
    <input type="search" id="q" placeholder="filter by title / company / skill…">
    <span class="cnt" id="cnt"></span>
    <label class="chk"><input type="checkbox" id="hideap"> hide applied</label>
    <span class="cnt" id="apcnt"></span>
    <button class="tool" id="export">export applied</button>
  </div>
  <ul class="offers" id="list"></ul>
</div>
<script>
const D = /*DATA*/;
const B = D.buckets, O = D.offers;
const F = {s:0,b:1,c:2,t:3,co:4,sk:5,w:6,u:7,city:8,lvl:9,wp:10,sal:11};
let selCat=null, selBucket=null;

// ---- "applied" state: persisted in the browser, keyed by a stable id per offer ----
// Survives reload AND survives  python browse.py  regenerating this file (same path = same
// storage). Never touches offers_db.jsonl. Export merges into applications_log.jsonl later.
const APPLIED = JSON.parse(localStorage.getItem('applied_offers')||'{}');
const keyOf = o => o[F.u] || (o[F.t]+'|'+o[F.co]);
function saveApplied(){localStorage.setItem('applied_offers',JSON.stringify(APPLIED));}
function apCount(){document.getElementById('apcnt').textContent=Object.keys(APPLIED).length+' applied';}

// ---- build the crosstab ----
const cats=[...new Set(O.map(o=>o[F.c]))];
const count={}, rowTot={}, colTot=Array(B.length).fill(0); let grand=0;
for(const c of cats){count[c]=Array(B.length).fill(0);rowTot[c]=0;}
for(const o of O){count[o[F.c]][o[F.b]]++;rowTot[o[F.c]]++;colTot[o[F.b]]++;grand++;}
// order categories by how many reach PLAUSIBLE+STRONG (best first)
const surv=c=>(count[c][4]+count[c][5])/rowTot[c];
cats.sort((a,b)=>surv(b)-surv(a));

const SHORT=["KILL","VETO","NEG","WEAK","PLAUS","STRONG"];
function grid(){
  let h='<table class="grid"><tr><th onclick="pick(null,null)">category ▾</th>';
  for(let b=0;b<B.length;b++) h+=`<th onclick="pick(null,${b})">${SHORT[b]}</th>`;
  h+='<th onclick="pick(null,null)">Σ</th></tr>';
  for(const c of cats){
    h+=`<tr><td class="cat" onclick="pick('${c}',null)">${c}</td>`;
    for(let b=0;b<B.length;b++){
      const n=count[c][b];
      const sel=(selCat===c&&selBucket===b)?' sel':'';
      h+=`<td class="n b${b}${n?'':' z'}${sel}" onclick="pick('${c}',${b})">${n||''}</td>`;
    }
    h+=`<td class="n tot" onclick="pick('${c}',null)">${rowTot[c]}</td></tr>`;
  }
  h+='<tr class="tot"><td class="cat" onclick="pick(null,null)">Σ</td>';
  for(let b=0;b<B.length;b++) h+=`<td class="n" onclick="pick(null,${b})">${colTot[b]}</td>`;
  h+=`<td class="n">${grand}</td></tr></table>`;
  document.getElementById('grid').innerHTML=h;
}
function pick(c,b){selCat=c;selBucket=b;grid();render();}

function esc(s){return (s||'').replace(/[&<>]/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[x]));}
function attrEsc(s){return esc(s).replace(/"/g,'&quot;');}
function whyHtml(w){
  return esc(w).replace(/\+[^−]+/g,m=>'<span class="pos">'+m+'</span>')
               .replace(/−.+$/,m=>'<span class="neg">'+m+'</span>');
}
function render(){
  const q=document.getElementById('q').value.toLowerCase().trim();
  const hideAp=document.getElementById('hideap').checked;
  let rows=O.filter(o=>
    (selCat===null||o[F.c]===selCat) &&
    (selBucket===null||o[F.b]===selBucket) &&
    (!hideAp||!APPLIED[keyOf(o)]) &&
    (!q||(o[F.t]+' '+o[F.co]+' '+o[F.sk]).toLowerCase().includes(q)));
  rows.sort((a,b)=>b[F.s]-a[F.s]);
  const name = (selCat||'all categories')+' · '+(selBucket===null?'all buckets':B[selBucket]);
  document.getElementById('selname').textContent=name;
  document.getElementById('cnt').textContent=rows.length+' offers';
  const lim=rows.slice(0,600);
  document.getElementById('list').innerHTML=lim.map((o,i)=>{
    const t=o[F.u]?`<a class="ttl" href="${o[F.u]}" target="_blank">${esc(o[F.t])}</a>`
                   :`<span class="ttl">${esc(o[F.t])}</span>`;
    const meta=[o[F.lvl],o[F.wp],o[F.city],o[F.sal]].filter(Boolean)
                 .map(x=>`<span class="badge">${esc(x)}</span>`).join(' ');
    const k=keyOf(o), ap=!!APPLIED[k];
    const btn=`<button class="applybtn" data-k="${attrEsc(k)}">${ap?'✓ applied':'mark applied'}</button>`;
    return `<li class="of lb${o[F.b]}${ap?' applied':''}"><div class="top"><span class="num">#${i+1}</span>`
      +`<span class="score">${o[F.s]>0?'+':''}${o[F.s]}</span>`
      +`${t} <span class="co">${esc(o[F.co])}</span> ${meta} ${btn}</div>`
      +`<div class="sk">${esc(o[F.sk])}</div>`
      +`<div class="why">${whyHtml(o[F.w])}</div></li>`;
  }).join('') + (rows.length>lim.length?`<li class="cnt">…and ${rows.length-lim.length} more (narrow with search)</li>`:'');
}
document.getElementById('q').addEventListener('input',render);
document.getElementById('hideap').addEventListener('change',render);

// toggle applied via event delegation (the list is rebuilt on every render)
document.getElementById('list').addEventListener('click',e=>{
  const b=e.target.closest('.applybtn'); if(!b) return;
  const k=b.dataset.k;
  if(APPLIED[k]) delete APPLIED[k]; else APPLIED[k]=new Date().toISOString();
  saveApplied(); apCount(); render();
});

// export the applied set as JSON you can fold into applications_log.jsonl
document.getElementById('export').addEventListener('click',()=>{
  const data=Object.entries(APPLIED).map(([k,at])=>({key:k,applied_at:at}));
  const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob); a.download='applied.json'; a.click();
});

apCount();
grid();render();
</script>
</body></html>"""

if __name__ == "__main__":
    main()
