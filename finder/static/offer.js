/* The offer row, shared by every page that lists offers.
   Renders the collapsed line (offerLi) and the panel it expands into (detailHtml), and wires
   the clicks inside a list (wireOfferList): expand/collapse, the tri-state pick button,
   "I applied by hand", the score override and the copy-prompt button.

   The host page supplies the context — which offers it holds and how to redraw itself — so the
   cockpit's grouped list and the harvest page's "new this run" list get the same row without
   either owning a copy of it. Styles live in static/offer.css; link both or neither. */

const esc=s=>(s||'').replace(/[&<>]/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[x]));
const attr=s=>esc(s).replace(/"/g,'&quot;');

// An offer is identified by title+company without the portal, so one posted on both collapses
// into a single row carrying both links — "jp" is that, not a duplicate.
const SITENAME={justjoin:'justjoin.it', pracuj:'pracuj.pl'};
function siteTitle(o){
  const names=(o.sources||[]).map(s=>SITENAME[s.site]||s.site);
  return names.length>1 ? 'on both portals: '+names.join(' + ') : 'on '+(names[0]||'?');
}
function srcLinks(o){
  const ss=(o.sources||[]).filter(s=>s.url);
  if(ss.length<2) return '';                       // the title already links the only source
  // One chip per PORTAL, not per link. A portal can hold several links to one job (a re-post
  // under a new slug, one posting per city); the row keeps them all so an application filed
  // through any of them still counts, but listing five chips would just bury the other portal.
  const bySite=new Map();
  for(const s of ss){ if(!bySite.has(s.site)) bySite.set(s.site,[]); bySite.get(s.site).push(s); }
  if(bySite.size<2 && ss.length<2) return '';
  const chips=[];
  for(const [site,list] of bySite){
    const s=list.find(x=>!x.archived_at)||list[0];
    const extra=list.length>1?` +${list.length-1}`:'';
    const tip=s.archived_at ? 'gone from this feed since '+s.archived_at.slice(0,10) : 'live';
    chips.push(`<a class="${s.archived_at?'dead':''}" href="${attr(s.url)}" target="_blank"`
      +` title="${attr(tip)}${list.length>1?` — ${list.length} postings of this job here`:''}"`
      +`>${esc(SITENAME[site]||site)}${extra} ↗</a>`);
  }
  return '<div class="srclinks">'+chips.join('')+'</div>';
}
function whyHtml(w){
  return esc(w).replace(/\+[^−]+/g,m=>'<span class="pos">'+m+'</span>')
               .replace(/−.+$/,m=>'<span class="neg">'+m+'</span>');
}

// The pick control: one button, three states, each click a server write.
//   empty -> queued           the nightly runner will apply to it
//   queued -> queued + dig    still queued, plus on the outreach list you work by hand
//   both -> empty             off both lists
// State comes off the offer object (o.queued / o.dig), which the API fills from the two files
// on every request — so a refresh, a second tab, or the runner draining the queue overnight
// all show the same thing without the page remembering anything.
function pickBtn(o){
  if(o.dig)    return `<button class="pick both" data-u="${attr(o.url)}"`
    +` title="queued AND on the dig-deeper list — click to drop both">✓🔎</button>`;
  if(o.queued) return `<button class="pick on" data-u="${attr(o.url)}"`
    +` title="queued for the nightly run — click to also dig deeper">✓</button>`;
  return `<button class="pick" data-u="${attr(o.url)}"`
    +` title="click to queue for the nightly run">☐</button>`;
}

// One offer row. `pick` is false on pages that do not pick offers (no button) — everything
// else about the row is the same either way.
function offerLi(o, pick){
  const applied=!!o.applied_by;
  const meta=[o.level,o.workplace,(o.cities||[]).join(', '),o.salary,o.stack]
    .filter(Boolean).map(x=>`<span class="badge">${esc(x)}</span>`).join(' ');
  let pill='';
  if(o.applied_by==='bot'){
    const oc=o.application?o.application.outcome:'';
    pill=`<span class="pill bot">bot · ${esc(oc)}</span>`;
  }else if(o.applied_by==='manual'){
    pill=`<span class="pill manual">applied by me</span>`;
  }
  const picker=(pick===false||applied)?'' : pickBtn(o);
  const isManual=o.applied_by==='manual';
  const mark=`<button class="markbtn${isManual?' on':''}" data-u="${attr(o.url)}">${isManual?'✓ applied by me':'I applied by hand'}</button>`;
  const title=o.url?`<a class="ttl" href="${attr(o.url)}" target="_blank" onclick="event.stopPropagation()">${esc(o.title)}</a>`
                   :`<span class="ttl">${esc(o.title)}</span>`;
  const newb=o.is_new?'<span class="newbadge">new</span>':'';
  const site=o.sites?`<span class="site s-${o.sites}" title="${attr(siteTitle(o))}">${esc(o.sites)}</span>`:'';
  const expb=o.archived
    ?`<span class="expbadge" title="off the feed since ${attr((o.archived_at||'').slice(0,10))}">expired</span>`:'';
  // From the sent log, so it outlives the dig card: a mailed card leaves the list, this stays.
  const mailed=o.emailed_at
    ?`<span class="mailed" title="you emailed them on ${attr(o.emailed_at.replace('T',' ').slice(0,16))}">✉</span>`:'';
  return `<li class="of lb${o.bucket}${applied?' applied':''}${o.archived?' expired':''}" data-u="${attr(o.url)}">
    <div class="row">
      ${picker}
      <span class="score">${o.score>0?'+':''}${o.score}</span>${o.score_override?'<span class="ovr" title="manual score">✎</span>':''}
      ${title} ${site} ${newb} ${expb} ${meta} ${pill} ${mailed} ${mark}
      <span class="caret">▸</span>
    </div>
    <div class="detail">${detailHtml(o)}</div>
  </li>`;
}

// The paste-into-Cowork prompt for ONE offer. Mirrors orchestrator_instructions.md §3's
// subagent task, minus the queue wrapper: read the two files, run mode review, this offer.
function applyPrompt(o){
  const offer={url:o.url, title:o.title, company:o.company,
               location:(o.cities||[]).join(', '), stack:o.stack};
  if(o.apply_method) offer.apply_method=o.apply_method;
  if(o.apply_url)    offer.apply_url=o.apply_url;
  return `You are the Applier. Apply to ONE job offer for Yan Lukashevich by driving his logged-in `
    +`Chrome via the claude-in-chrome tools.\n\n`
    +`Read and follow these two files in this folder, exactly:\n`
    +`  - applier_instructions.md  (behavior, rules, the loop, logging)\n`
    +`  - profile.md               (the sole source of truth for facts)\n\n`
    +`Run mode: review   (fill everything, then STOP before the final Submit)\n\n`
    +`The one offer to handle:\n${JSON.stringify(offer, null, 2)}\n\n`
    +`Follow the playbook end to end, including appending your outcome to `
    +`applications_log.jsonl (and todo_manual.md if blocked). Then report back with the exact `
    +`JSON object you logged.`;
}

/* The offer's own text — the duties and requirements no listing page carries. Downloaded by
   finder/descriptions.py (slowly, after each harvest) and fetched one row at a time here: the
   list holds thousands of offers and the panel only ever shows one.
   Kept in a page-level Map so a re-render — a pick click, a saved score — redraws the text
   from memory instead of asking the server again. */
const DESCS=new Map();

// justjoin's body has no headings of its own, so its two section types are drawn without one.
const UNTITLED=new Set(['description','bullets']);
// pracuj types its sections instead. An unknown type falls through to its raw name, which is
// readable enough and says a new section type has appeared.
const SECLABEL={
  'about-project':'About the project', responsibilities:'Your responsibilities',
  'requirements-expected':'Requirements', 'requirements-optional':'Nice to have',
  'technologies-expected':'Technologies — expected', 'technologies-optional':'Technologies — optional',
  'technologies-os':'Operating systems', 'development-practices':'Development practices',
  'work-organization-work-style':'How the work is organised',
  'work-organization-team-size':'Team size', 'work-organization-team-members':'The team',
  'recruitment-stages':'Recruitment stages', offered:'What they offer', benefits:'Benefits',
  'training-space':'Training', 'additional-module':'More from the employer',
  'about-us':'About the company', 'about-us-description':'About the company'};

function descBody(rec){
  if(!rec||rec.status!=='ok') return '<div class="descnote">No description on the portal page.</div>';
  const secs=(rec.sections||[]).filter(s=>(s.items||[]).length);
  if(!secs.length) return '<div class="descnote">The portal page carried no text.</div>';
  return secs.map(s=>{
    // `description` is prose — the paragraphs were paragraphs before the HTML was stripped, and
    // bulleting them would invent structure the offer never had. Everything else IS a list.
    const body=s.type==='description'
      ? s.items.map(t=>`<p>${esc(t)}</p>`).join('')
      : `<ul>${s.items.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>`;
    const head=UNTITLED.has(s.type)
      ? '' : `<div class="dsec">${esc(SECLABEL[s.type]||s.type)}</div>`;
    return head+body;
  }).join('');
}

// What the box holds before anything is fetched. o.desc is the status the API joined on:
// "ok" = downloaded, fill it when the row opens; "gone" = the portal deleted the offer;
// nothing = never fetched, so offer the button.
function descHtml(o){
  const box=b=>`<div class="desc" data-u="${attr(o.url)}">${b}</div>`;
  const rec=DESCS.get(o.url);
  if(rec) return box(descBody(rec));
  if(o.desc==='gone') return box('<div class="descnote">The portal no longer has this offer — '
    +'nothing left to download.</div>');
  if(o.desc==='ok') return box('<div class="descnote">loading…</div>');
  return box('<div class="descnote">No description downloaded yet — the background pass only '
    +'takes offers from the last seven days.</div>'
    +`<button class="descbtn" data-u="${attr(o.url)}">⤓ Fetch description</button>`);
}

// One request per opened row, and only for an offer the server says it has text for.
async function loadDesc(li, ctx){
  const box=li.querySelector('.desc');
  if(!box||box.dataset.done) return;
  const o=ctx.find(box.dataset.u);
  if(!o||o.desc!=='ok'||DESCS.has(o.url)) return;
  box.dataset.done='1';
  try{
    const r=await fetch('/api/description?url='+encodeURIComponent(o.url));
    const rec=await r.json();
    if(rec&&rec.status==='ok') DESCS.set(o.url, rec);
    box.innerHTML=descBody(rec);
  }catch(err){
    delete box.dataset.done;                       // a dropped request is worth one more click
    box.innerHTML=`<div class="descnote err">could not load: ${esc(err.message)}</div>`;
  }
}

function detailHtml(o){
  let h='';
  if(o.archived) h+=`<div class="expnote">Expired — gone from every feed that carried it, since the harvest of
    ${esc((o.archived_at||'').replace('T',' ').slice(0,16))}. Kept as history; the link is probably dead.</div>`;
  h+=`<div class="skills">${esc((o.skills||[]).join(' · '))||'—'}</div>`;
  h+=`<div class="why">${whyHtml(o.why)}</div>`;
  h+=srcLinks(o);
  h+=descHtml(o);
  const a=o.application;
  if(a){
    const answers=(a.composed_answers||[]).filter(Boolean);
    h+=`<dl>
      <dt>applied</dt><dd class="out-${esc(a.outcome)}">${esc(a.outcome)} · ${esc(a.apply_type||'')}</dd>
      <dt>when</dt><dd>${esc((a.timestamp||'').replace('T',' ').slice(0,19))}</dd>
      <dt>CV used</dt><dd>${esc(a.cv_used||'—')}</dd>
      ${a.blocked_reason?`<dt>blocked</dt><dd class="neg">${esc(a.blocked_reason)}</dd>`:''}
    </dl>`;
    if(answers.length){
      h+=`<div class="cnt">free-text entered:</div>`;
      h+=answers.map(t=>`<div class="freetext">${esc(typeof t==='string'?t:JSON.stringify(t))}</div>`).join('');
    }
    if(a.notes) h+=`<div class="notes">${esc(a.notes)}</div>`;
  }else if(o.manual_at){
    h+=`<dl><dt>applied by me</dt><dd>${esc(o.manual_at.replace('T',' ').slice(0,19))}</dd></dl>`;
  }else{
    h+=`<div class="cnt" style="margin-top:6px">not applied yet</div>`;
  }
  h+=`<div class="scoreedit">
    <div class="head cnt">Adjust score &amp; reason (overrides the auto score for sorting and display):</div>
    <div class="scorerow">
      <input type="number" class="scoreinput" data-u="${attr(o.url)}" value="${o.score}" step="1">
      <textarea class="scorereason" data-u="${attr(o.url)}" placeholder="why this score? (your note)">${esc(o.score_reason||'')}</textarea>
      <button class="scorebtn" data-u="${attr(o.url)}">Save</button>
    </div>
    ${o.score_override?`<div class="scoremeta">manual override · auto score was ${o.base_score>0?'+':''}${o.base_score}</div>`:''}
  </div>`;
  h+=`<div class="applyprompt">
    <div class="head">
      <div class="cnt">Cowork prompt — paste into a fresh Cowork agent to apply to this one offer:</div>
      <button class="copybtn" data-u="${attr(o.url)}">Copy prompt</button>
    </div>
    <pre class="prompt">${esc(applyPrompt(o))}</pre>
  </div>`;
  return h;
}

// Flash "✓ Copied" on a button while the text goes to the clipboard. Two callers: the
// per-offer apply prompt and the dig-deeper list export.
async function copyFlash(btn, text){
  try{
    await navigator.clipboard.writeText(text);
    const label=btn.textContent; btn.textContent='✓ Copied'; btn.classList.add('done');
    setTimeout(()=>{btn.textContent=label; btn.classList.remove('done');},1800);
  }catch(err){ alert('Copy failed: '+err.message); }
}

// An outreach card's stage chip plus the ✓ that says its contacts are found. Shared by the
// cockpit's dig tab and /outreach, so the two never label a card differently.
const STAGECLS={'no contact':'none',contacts:'contacts',draft:'draft',approved:'approved'};
function stageChip(d){
  return `<span class="stg s-${STAGECLS[d.stage]||'none'}">${esc(d.stage||'?')}</span>`
    +(d.has_contacts?`<span class="found" title="contacts found">✓</span>`:'');
}

// The dig-deeper list as a checklist you can paste anywhere — one line per company to chase.
function digMarkdown(items){
  return items.map(d=>`- [ ] ${d.company} — ${d.title} — ${d.url}`
    +(d.email?` — ${d.email}`:'')+(d.note?` — ${d.note}`:'')).join('\n');
}

// Drop an offer's dig card. The server refuses a card that holds contacts or a draft unless
// asked twice, so ten minutes of digging never vanish on a stray click; true if it is gone.
async function dropDig(url, label){
  const post=force=>fetch('/api/dig/remove',{method:'POST',
    headers:{'content-type':'application/json'},body:JSON.stringify({url,force})})
    .then(r=>r.json());
  const d=await post(false);
  if(!d.needs_force) return !d.error;
  if(!confirm(`${label||'This card'} has contacts or an email draft on it.\n\n`
      +'Drop it from the dig-deeper list anyway? What was filled in is lost.')) return false;
  return !(await post(true)).error;
}

// One click on the pick button = one server write. The next state is read off the CURRENT
// one, so the cycle is empty -> queued -> queued+dig -> empty. Nothing is kept in the page:
// the response is applied to the offer object and the list is redrawn from it.
async function cyclePick(o){
  const post=(p)=>fetch(p,{method:'POST',headers:{'content-type':'application/json'},
    body:JSON.stringify({url:o.url})});
  if(o.dig){        if(!await dropDig(o.url, o.company)) return;   // kept: both lists stay
                    await post('/api/queue/remove');
                    o.queued=false; o.dig=false; }
  else if(o.queued){ await post('/api/dig/add');   o.dig=true; }
  else{              await post('/api/queue/add'); o.queued=true; }
}

/* Delegated clicks for a container of offer rows. ctx:
     find(url)  -> the page's offer object for that url (so a mark or a score edit updates the
                   copy the page re-renders from), or undefined
     refresh()  -> redraw the list
     onPick()   -> called after a pick changed the queue or the dig list, so the host page can
                   re-fetch its panel; optional
   Clicks outside an offer row are ignored, so a page can attach its own handlers (company
   headers, filters) to the same element. */
function wireOfferList(el, ctx){
  el.addEventListener('click',async e=>{
    const pick=e.target.closest('.pick');
    if(pick){ e.stopPropagation();
      const o=ctx.find(pick.dataset.u);
      if(o){ await cyclePick(o); ctx.refresh(); ctx.onPick&&ctx.onPick(); }
      return; }
    const mark=e.target.closest('.markbtn');
    if(mark){ e.stopPropagation();
      const r=await fetch('/api/manual',{method:'POST',headers:{'content-type':'application/json'},
        body:JSON.stringify({url:mark.dataset.u})});
      const d=await r.json();
      const o=ctx.find(d.url);
      if(o){ o.manual_at=d.manual_at;
        o.applied_by = o.application ? 'bot' : (d.manual_at ? 'manual' : null); }
      ctx.refresh(); return; }
    const sbtn=e.target.closest('.scorebtn');
    if(sbtn){ e.stopPropagation();
      const box=sbtn.closest('.scoreedit');
      const score=parseInt(box.querySelector('.scoreinput').value,10);
      if(Number.isNaN(score)){ alert('Score must be a whole number'); return; }
      const reason=box.querySelector('.scorereason').value;
      const url=sbtn.dataset.u;
      const r=await fetch('/api/score',{method:'POST',headers:{'content-type':'application/json'},
        body:JSON.stringify({url, score, reason})});
      const d=await r.json();
      const o=ctx.find(url);
      // base_score already holds the auto score from the API — never overwrite it here.
      if(o){ o.score=d.score; o.score_reason=d.reason; o.score_override=true; o.score_at=d.at; }
      sbtn.textContent='✓ Saved'; sbtn.classList.add('done');
      // re-sort/relabel with the new score after a beat so the "✓ Saved" flash is visible
      setTimeout(ctx.refresh,650);
      return; }
    const dbtn=e.target.closest('.descbtn');
    if(dbtn){ e.stopPropagation();
      const o=ctx.find(dbtn.dataset.u);
      const box=dbtn.closest('.desc');
      if(!o||!box) return;
      box.innerHTML='<div class="descnote">downloading…</div>';
      const r=await fetch('/api/description/fetch',{method:'POST',
        headers:{'content-type':'application/json'},body:JSON.stringify({url:o.url})});
      const rec=await r.json();
      if(rec.error){ box.innerHTML=`<div class="descnote err">${esc(rec.error)}</div>`; return; }
      // the row keeps the new status, so a later re-render draws the text, not the button
      o.desc=rec.status;
      if(rec.status==='ok') DESCS.set(o.url, rec);
      box.innerHTML=descBody(rec);
      return; }
    const copy=e.target.closest('.copybtn');
    if(copy){ e.stopPropagation();
      const o=ctx.find(copy.dataset.u);
      if(o) await copyFlash(copy, applyPrompt(o));
      return; }
    // the detail body is for reading/copying -- a mouse-up ending a selection fires a click too,
    // and toggling there would collapse the panel out from under the text you just highlighted
    if(e.target.closest('.detail')) return;
    const li=e.target.closest('li.of');
    if(!li || e.target.closest('a')) return;
    const s=window.getSelection();
    if(s && !s.isCollapsed && s.toString().trim() && li.contains(s.anchorNode)) return;
    li.classList.toggle('open');
    if(li.classList.contains('open')) loadDesc(li, ctx);
  });
}
