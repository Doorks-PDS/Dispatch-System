/* Read-only existing PDS job handoff after Moses document extraction.
   Exact saved identifiers only; no auto-merge or record modifications. */
(function(root){
  'use strict';
  const val=x=>String(x==null?'':x).trim();
  const node=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=String(text);return el;};
  async function check(fields){
    const job_number=val(fields?.job_number),estimate_number=val(fields?.estimate_number);
    if(!job_number&&!estimate_number)return {found:false,candidates:[],match_basis:'no_references'};
    const response=await fetch('/dispatch-ai/match-existing',{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({job_number,estimate_number})});
    const body=await response.json();
    if(!response.ok)throw new Error(body.detail||'Saved job lookup unavailable');
    return body;
  }
  async function mount({host,fields,onOpen}){
    if(!host)return;
    host.querySelector('[data-moses-existing-job]')?.remove();
    const wrap=node('section');wrap.dataset.mosesExistingJob='true';
    wrap.style.cssText='display:grid;gap:8px;margin:12px 0;padding:13px;border:1px solid #d2dce5;border-radius:12px;background:#f8fafc';
    wrap.append(node('strong','Existing PDS job check'));
    const status=node('div','Checking saved job/estimate references…');status.setAttribute('role','status');wrap.append(status);host.append(wrap);
    try{
      const result=await check(fields);
      if(!result.found){status.textContent=result.match_basis==='no_references'
        ?'No job or estimate number extracted. Select an existing job manually if this document refers to one.'
        :'No exact job/estimate reference found. This does not prove the service is new—review before saving.';return result;}
      status.textContent=result.conflict?'Multiple or conflicting saved references; select the correct job manually.':
        'Saved job found. Review this existing record before creating any new dispatch.';
      for(const candidate of result.candidates||[]){
        const card=node('article');card.style.cssText='border:1px solid #c8d7df;border-radius:9px;padding:10px;display:grid;gap:5px;background:#fff';
        card.append(node('strong',[candidate.customer||'PDS customer',candidate.job_number?'Job #'+candidate.job_number:''].filter(Boolean).join(' · ')));
        card.append(node('small',[candidate.address,candidate.status,
          candidate.estimate_number?'Saved estimate #'+candidate.estimate_number:''].filter(Boolean).join(' · ')));
        if(candidate.estimate_reference_unlinked) card.append(node('small','The PDF estimate number is not linked to this saved job. Review before updating the ticket.'));
        card.append(node('small',[candidate.matched_job_number?'Exact job # match':'',
          candidate.matched_estimate_number?'Exact estimate # match':''].filter(Boolean).join(' + ')));
        if(typeof onOpen==='function') {
          const open=node('button','Open this existing PDS ticket');open.className='btn btn-orange';open.type='button';
          open.addEventListener('click',()=>onOpen(candidate));card.append(open);
        }
        if(!result.conflict && candidate.matched_job_number && root.MosesDocumentChanges){
          const review=node('button','Compare PDF with saved ticket');review.className='btn';review.type='button';
          review.onclick=()=>root.MosesDocumentChanges.mount({host,fields,candidate});card.append(review);
        }
        wrap.append(card);
      }
      const note=node('small','Read-only lookup. Existing ticket edits are made through the normal PDS job editor, not by merging PDF text automatically.');wrap.append(note);
      return result;
    }catch(error){status.textContent='Saved-job verification unavailable: '+(error.message||error)+'. Check All Jobs before saving.';return {error:true};}
  }
  root.MosesDocumentMatch={check,mount};
  if(typeof module==='object'&&module.exports)module.exports={check};
})(typeof window!=='undefined'?window:globalThis);
