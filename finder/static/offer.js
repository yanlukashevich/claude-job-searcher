/* The offer row, shared by every page that lists offers.
   Renders the collapsed line (offerLi) and the panel it expands into (detailHtml), and wires
   the clicks inside a list (wireOfferList): expand/collapse, the pick checkbox, "I applied by
   hand", the score override and the copy-prompt button.

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

// One offer row. `sel` is the worklist selection Set, or null on pages that do not pick offers
// (no Set, no checkbox) — everything else about the row is the same either way.
function offerLi(o, sel){
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
  const checkbox=(!sel||applied)?'' :
    `<input type="checkbox" class="pick" data-u="${attr(o.url)}" ${sel.has(o.url)?'checked':''}>`;
  const isManual=o.applied_by==='manual';
  const mark=`<button class="markbtn${isManual?' on':''}" data-u="${attr(o.url)}">${isManual?'✓ applied by me':'I applied by hand'}</button>`;
  const title=o.url?`<a class="ttl" href="${attr(o.url)}" target="_blank" onclick="event.stopPropagation()">${esc(o.title)}</a>`
                   :`<span class="ttl">${esc(o.title)}</span>`;
  const newb=o.is_new?'<span class="newbadge">new</span>':'';
  const site=o.sites?`<span class="site s-${o.sites}" title="${attr(siteTitle(o))}">${esc(o.sites)}</span>`:'';
  const expb=o.archived
    ?`<span class="expbadge" title="off the feed since ${attr((o.archived_at||'').slice(0,10))}">expired</span>`:'';
  return `<li class="of lb${o.bucket}${applied?' applied':''}${o.archived?' expired':''}" data-u="${attr(o.url)}">
    <div class="row">
      ${checkbox}
      <span class="score">${o.score>0?'+':''}${o.score}</span>${o.score_override?'<span class="ovr" title="manual score">✎</span>':''}
      ${title} ${site} ${newb} ${expb} ${meta} ${pill} ${mark}
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

function detailHtml(o){
  let h='';
  if(o.archived) h+=`<div class="expnote">Expired — gone from every feed that carried it, since the harvest of
    ${esc((o.archived_at||'').replace('T',' ').slice(0,16))}. Kept as history; the link is probably dead.</div>`;
  h+=`<div class="skills">${esc((o.skills||[]).join(' · '))||'—'}</div>`;
  h+=`<div class="why">${whyHtml(o.why)}</div>`;
  h+=srcLinks(o);
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

/* Delegated clicks for a container of offer rows. ctx:
     find(url)  -> the page's offer object for that url (so a mark or a score edit updates the
                   copy the page re-renders from), or undefined
     refresh()  -> redraw the list
     sel        -> the worklist selection Set, or null on pages that do not pick
     onSel()    -> called after the selection changed
   Clicks outside an offer row are ignored, so a page can attach its own handlers (company
   headers, filters) to the same element. */
function wireOfferList(el, ctx){
  const sel=ctx.sel||null;
  el.addEventListener('click',async e=>{
    const pick=e.target.closest('.pick');
    if(pick){ e.stopPropagation();
      if(sel){ if(pick.checked) sel.add(pick.dataset.u); else sel.delete(pick.dataset.u); }
      ctx.onSel&&ctx.onSel(); return; }
    const mark=e.target.closest('.markbtn');
    if(mark){ e.stopPropagation();
      const r=await fetch('/api/manual',{method:'POST',headers:{'content-type':'application/json'},
        body:JSON.stringify({url:mark.dataset.u})});
      const d=await r.json();
      const o=ctx.find(d.url);
      if(o){ o.manual_at=d.manual_at;
        o.applied_by = o.application ? 'bot' : (d.manual_at ? 'manual' : null);
        if(o.applied_by && sel) sel.delete(o.url); }
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
    const copy=e.target.closest('.copybtn');
    if(copy){ e.stopPropagation();
      const o=ctx.find(copy.dataset.u);
      if(o){
        try{
          await navigator.clipboard.writeText(applyPrompt(o));
          const label=copy.textContent; copy.textContent='✓ Copied'; copy.classList.add('done');
          setTimeout(()=>{copy.textContent=label; copy.classList.remove('done');},1800);
        }catch(err){ alert('Copy failed: '+err.message); }
      }
      return; }
    // the detail body is for reading/copying -- a mouse-up ending a selection fires a click too,
    // and toggling there would collapse the panel out from under the text you just highlighted
    if(e.target.closest('.detail')) return;
    const li=e.target.closest('li.of');
    if(!li || e.target.closest('a')) return;
    const s=window.getSelection();
    if(s && !s.isCollapsed && s.toString().trim() && li.contains(s.anchorNode)) return;
    li.classList.toggle('open');
  });
}
