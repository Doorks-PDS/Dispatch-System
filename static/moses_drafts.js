/* Persistent Moses PDS quote review tickets; no document send/issue actions here. */
(()=>{
'use strict';
const url='/moses-drafts';
const h=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!=null)e.textContent=txt;if(cls)e.className=cls;return e};
const request=async(path,method='GET',data)=>{
  const r=await fetch(url+path,{method,credentials:'same-origin',headers:data?{'Content-Type':'application/json'}:undefined,body:data?JSON.stringify(data):undefined});
  let result;try{result=await r.json()}catch{throw Error('Unable to read Moses draft response')}
  if(!r.ok)throw Error(typeof result.detail==='string'?result.detail:'Moses draft request failed');return result;
};
let panel,body,feedback;
function mount(){
 if(document.getElementById('mosesDraftsLaunch'))return;
 const launch=h('button','Moses Drafts','btn');launch.type='button';launch.id='mosesDraftsLaunch';
 launch.hidden=true;launch.style.display='none';
 const openDrafts=()=>{if(document.body.dataset.platform!=='pds')return;panel.hidden=false;panel.style.display='flex';render()};
 launch.onclick=openDrafts;
 window.openMosesDrafts=openDrafts;
 panel=h('section');panel.id='mosesDraftsPanel';panel.hidden=true;panel.style.cssText='position:fixed;inset:6vh max(14px,calc((100vw - 1100px)/2));z-index:11100;display:flex;flex-direction:column;background:#fff;border-radius:18px;box-shadow:0 15px 70px #0006;border:1px solid #dce5dd;overflow:hidden';
 const heading=h('div');heading.style.cssText='display:flex;justify-content:space-between;align-items:center;gap:12px;padding:16px 20px;border-bottom:1px solid #e4e9e6';
 const title=h('strong','Moses · Quote drafts');const close=h('button','Close ×','btn');close.onclick=()=>{panel.hidden=true;panel.style.display='none'};heading.append(title,close);
 const instructions=h('div');instructions.hidden=true;
 const controls=h('div');controls.style.cssText='padding:12px 20px;display:flex;gap:10px;flex-wrap:wrap';
 const prepare=h('button','Prepare quote reviews','btn btn-orange');prepare.onclick=async()=>{prepare.disabled=true;try{const result=await request('/prepare','POST');announce(`${result.created} new review tickets saved. Existing review decisions were preserved.`);await render()}catch(e){announce(e.message)}finally{prepare.disabled=false}};
 const refresh=h('button','Refresh drafts','btn');refresh.onclick=render;
 controls.append(prepare,refresh);
 feedback=h('small');feedback.setAttribute('role','status');feedback.style.cssText='padding:0 20px 10px;color:#45624f';
 body=h('div');body.style.cssText='overflow:auto;flex:1;padding:4px 20px 22px';
 panel.style.display='none';panel.append(heading,instructions,controls,feedback,body);document.body.append(launch,panel);
 const visibility=()=>{const visible=document.body.dataset.platform==='pds';launch.hidden=!visible;if(!visible){panel.hidden=true;panel.style.display='none'}};
 visibility();const observer=new MutationObserver(visibility);observer.observe(document.body,{attributes:true,attributeFilter:['data-platform']});
}
function announce(s){if(feedback)feedback.textContent=s}
function field(label,value,onchange,type='text'){
 const wrap=h('label');wrap.style.cssText='display:grid;gap:5px;font-size:12px;font-weight:700;color:#53655b';wrap.append(h('span',label));
 const ctl=h(type==='textarea'?'textarea':'input');ctl.className='input';ctl.value=value||'';if(type==='textarea'){ctl.rows=4;ctl.style.minHeight='88px'}ctl.oninput=()=>onchange(ctl.value);wrap.append(ctl);return wrap;
}
function select(label,choices,value,onchange){const wrap=h('label');wrap.style.cssText='display:grid;gap:5px;font-size:12px;font-weight:700;color:#53655b';wrap.append(h('span',label));const ctl=h('select');ctl.className='input';for(const [key,text] of choices){const o=h('option',text);o.value=key;ctl.append(o)}ctl.value=value||'';ctl.onchange=()=>onchange(ctl.value);wrap.append(ctl);return wrap}
async function render(){
 if(!body)return;body.replaceChildren();announce('Loading saved Moses review tickets…');
 let rows;try{rows=(await request('')).items||[]}catch(e){announce(e.message);return}
 announce(`${rows.length} drafts`);
 if(!rows.length){body.append(h('p','No saved Moses review tickets. Select “Find eligible PDS quotes” to examine current quote-ready recommendation forms.','hint'));return}
 const counts=h('div');counts.style.cssText='display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 14px';
 for(const [key,label] of [['pending_review','Needs review'],['ready_for_estimator','Approved for estimator'],['declined','Declined']]){const n=rows.filter(x=>x.state===key).length;const pill=h('span',`${label}: ${n}`);pill.style.cssText='border:1px solid #d9e5db;padding:5px 10px;border-radius:100px;font-size:12px';counts.append(pill)}body.append(counts);
 const grid=h('div');grid.style.cssText='display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,360px),1fr));gap:12px';body.append(grid);
 for(const item of rows){
  const card=h('article');card.style.cssText='border:1px solid #d9e1dc;border-left:5px solid '+(item.state==='ready_for_estimator'?'#26835c':item.state==='declined'?'#8993a0':'#d99731')+';border-radius:12px;background:white;padding:15px;display:grid;gap:9px;align-content:start';
  const name=h('strong',item.customer||'Unnamed customer');name.style.fontSize='15px';const meta=h('small','Job #'+(item.job_number||'—')+' · '+(item.job_status||'')+' · '+(item.date||''));meta.style.color='#67756e';const status=h('div',item.state==='pending_review'?'Awaiting office decision':item.state==='ready_for_estimator'?'Approved for estimator':'Declined');status.style.fontWeight='700';status.style.fontSize='12px';
  const scope=h('p',item.scope||'Parts/freight details require review');scope.style.cssText='margin:0;white-space:pre-wrap;overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;font-size:13px';
  const actions=h('div');actions.style.cssText='display:flex;flex-wrap:wrap;gap:7px';
  const review=h('button','Review','btn');review.onclick=()=>openEditor(item);actions.append(review);
  const ticket=h('button','View Job','btn');ticket.onclick=()=>{panel.hidden=true;panel.style.display='none';document.dispatchEvent(new CustomEvent('moses-open-pds-job',{detail:{job_id:item.job_id}}))};actions.append(ticket);
  if(item.state!=='pending_review'){
    const reopen=h('button','Reopen','btn');reopen.onclick=async()=>{reopen.disabled=true;try{await request('/'+encodeURIComponent(item.id)+'/reopen','POST',{version:item.version});await render()}catch(e){announce(e.message)}finally{reopen.disabled=false}};actions.append(reopen);
  }
  const archive=h('button','Remove','btn');archive.onclick=async()=>{if(!window.confirm('Remove this draft from the list? Its audit history will be preserved.'))return;archive.disabled=true;try{await request('/'+encodeURIComponent(item.id)+'/archive','POST',{version:item.version});await render()}catch(e){announce(e.message)}finally{archive.disabled=false}};actions.append(archive);
  if(item.state==='ready_for_estimator'){
    const estimate=h('button','Open Estimator','btn btn-orange');
    estimate.onclick=()=>document.dispatchEvent(new CustomEvent('moses-open-pds-estimator',{detail:{job_id:item.job_id,draft_id:item.id}}));
    const delivery=h('button','Email / Delivery','btn');
    delivery.onclick=()=>openDelivery(item);
    actions.append(estimate,delivery);
  }
  card.append(name,meta,status,scope,actions);grid.append(card);
 }
}
// Official document delivery is delegated to the existing PDS Resend approval service.
// This view never creates a PDF or sends based on the Moses review approval alone.
async function openDelivery(ticket){
 const veil=h('div');veil.style.cssText='position:fixed;inset:0;z-index:11120;background:#12291b99;display:flex;align-items:center;justify-content:center;padding:12px';
 const dialog=h('section');dialog.style.cssText='background:#fff;border-radius:16px;width:min(740px,100%);max-height:92vh;overflow:auto;padding:20px;display:grid;gap:12px';
 const heading=h('div');heading.style.cssText='display:flex;justify-content:space-between;align-items:center;gap:10px';
 heading.append(h('h3','Estimate delivery · '+(ticket.customer||'PDS job')));
 const close=h('button','Close ×','btn');close.onclick=()=>veil.remove();heading.append(close);dialog.append(heading);
 dialog.append(h('p','Select an actual saved estimate PDF. Moses checks the linked job and the existing Resend workflow separately verifies the recipient, attachment and sender. An email is sent only after explicit final approval.','hint'));
 const status=h('p');status.setAttribute('role','status');status.style.whiteSpace='pre-wrap';
 const docHost=h('div');docHost.style.cssText='display:grid;gap:12px';
 const reload=h('button','Refresh official documents','btn');reload.onclick=load;
 dialog.append(reload,status,docHost);veil.append(dialog);document.body.append(veil);
 const emailApi=async(path,method='GET',data)=>{
   const response=await fetch('/moses-pds-email'+path,{method,credentials:'same-origin',headers:data?{'Content-Type':'application/json'}:undefined,body:data?JSON.stringify(data):undefined});
   const payload=await response.json().catch(()=>({}));
   if(!response.ok)throw Error(String(payload.detail||'Document email request failed'));
   return payload;
 };
 let refreshGeneration=0;
 async function load(){
  const generation=++refreshGeneration;
  status.textContent='Looking for official saved estimates linked to this job…';docHost.replaceChildren();reload.disabled=true;
  try{
   const data=await request('/'+encodeURIComponent(ticket.id)+'/delivery');
   if(generation!==refreshGeneration)return;
   status.textContent=data.count?`${data.count} saved linked estimate(s). Choose the correct document.`:'No saved estimate is linked to this job yet. Open the estimator, finish review, and generate the official PDF first.';
   for(const doc of data.items||[]){
     const block=h('article');block.style.cssText='border:1px solid #d9e1dc;padding:13px;border-radius:12px;display:grid;gap:9px';
     block.append(h('strong',doc.number+' · '+doc.filename));
     const details=h('small','Verify the recipient and PDF before sending. No automatic email will be sent.');block.append(details);
     const outcomes=h('div');outcomes.style.cssText='display:grid;gap:6px';block.append(outcomes);
     const controls=h('div');controls.style.cssText='display:flex;gap:8px;flex-wrap:wrap';block.append(controls);
     const preview=h('button','Verify recipient & PDF','btn');
     const history=h('button','Delivery history','btn');
     controls.append(preview,history);
     const path='/estimate/'+encodeURIComponent(doc.number);
     const showHistory=async()=>{
       try{const events=await emailApi(path+'/history');outcomes.replaceChildren();
         const rows=Array.isArray(events.items)?events.items:[];
         if(!rows.length){outcomes.append(h('small','No saved send attempts for this document.'));return}
         for(const event of rows.slice(-8).reverse()){
           outcomes.append(h('small',`${String(event.state||'unknown')} · ${String(event.delivery_status||'not_confirmed')} · ${String(event.to||'')}`));
         }
       }catch(e){details.textContent='Delivery history unavailable: '+e.message}
     };
     history.onclick=showHistory;
     preview.onclick=async()=>{
       preview.disabled=true;details.textContent='Verifying PDF and linked customer contact…';
       try{
         const verified=await emailApi(path+'/preview');
         if(!verified.ready_for_approval||!verified.attachment_verified||String(verified.job_id)!==String(ticket.job_id))throw Error('Document is not verified against this Moses ticket');
         details.textContent='Recipient: '+verified.to+' · Attachment: '+verified.filename+' · Sender: '+verified.from+' · Reply to: '+verified.reply_to;
         const prepare=h('button','Prepare send approval','btn btn-orange');controls.append(prepare);
         prepare.onclick=async()=>{
           prepare.disabled=true;
           try{
             // Recheck the linked document before asking the provider service for a proposal.
             const current=await request('/'+encodeURIComponent(ticket.id)+'/delivery');
             if(!(current.items||[]).some(row=>row.number===doc.number))throw Error('Document no longer linked to this Moses ticket');
             const proposed=await emailApi(path+'/proposal','POST');
             const action=proposed.proposal;
             if(!action||!action.id||action.number!==doc.number||!proposed.approval_required)throw Error('Valid send approval was not returned');
             prepare.remove();
             const decision=h('div');decision.style.cssText='display:grid;gap:7px;background:#fff8eb;padding:12px;border-radius:10px';
             decision.append(h('strong','Final email approval · '+action.number));
             decision.append(h('small','To: '+action.to+' · Attachment: '+action.filename+' · This may send a real customer email.'));
             const buttons=h('div');buttons.style.cssText='display:flex;gap:8px;flex-wrap:wrap';
             for(const [approve,label] of [[true,'Approve & send via Resend'],[false,'Reject sending']]){
               const button=h('button',label,'btn');buttons.append(button);
               button.onclick=async()=>{
                 if(approve&&!window.confirm('SEND '+action.number+' to '+action.to+' via Resend? This is a real external action.'))return;
                 for(const b of buttons.querySelectorAll('button'))b.disabled=true;
                 details.textContent='Decision submitted. Checking saved provider outcome…';
                 try{
                   const outcome=await emailApi('/proposals/'+encodeURIComponent(action.id)+'/decision','POST',{approve});
                   // Do not offer a second send attempt when provider status is unknown.
                   details.textContent=outcome.sent?'Resend accepted the email; recipient delivery is not yet confirmed.':
                     outcome.state==='uncertain'?'Provider outcome uncertain. Do NOT resend without manual verification.':
                     outcome.state==='rejected'?'Send rejected; no email was sent.':
                     'No successful send confirmed: '+String(outcome.state||'unknown');
                   await showHistory();
                 }catch(e){details.textContent='Send decision outcome NOT CONFIRMED: '+e.message+' · Check saved delivery history. Do not retry blindly.';await showHistory()}
               };
             }
             decision.append(buttons);block.append(decision);
           }catch(e){details.textContent='Could not prepare approval: '+e.message;prepare.disabled=false}
         };
       }catch(e){details.textContent='Verification failed: '+e.message}
       finally{preview.disabled=false}
     };
     docHost.append(block);
     await showHistory();
   }
  }catch(e){status.textContent='Could not verify linked documents: '+e.message}
  finally{reload.disabled=false}
 }
 await load();
}
function openEditor(original){
 const item={...original,selected_parts:[...(original.selected_parts||[])]};const backdrop=h('div');backdrop.style.cssText='position:fixed;inset:0;background:#15241b85;z-index:11110;display:flex;align-items:center;justify-content:center;padding:12px';
 const dialog=h('section');dialog.style.cssText='width:min(760px,100%);max-height:94vh;overflow:auto;background:#fff;border-radius:16px;padding:22px;box-sizing:border-box';
 const top=h('div');top.style.cssText='display:flex;justify-content:space-between;align-items:center;gap:12px';top.append(h('h3',`${item.customer} · #${item.job_number||'—'}`));const close=h('button','Close ×','btn');close.onclick=()=>backdrop.remove();top.append(close);dialog.append(top);
 const note=h('p');note.hidden=true;
 const form=h('div');form.style.cssText='display:grid;gap:12px';
 form.append(field('Proposed work / estimate description',item.scope,v=>{item.scope=v},'textarea'));
 const parts=h('div','Parts requested: '+(item.parts_required||'No parts specified'));parts.style.cssText='font-size:13px;white-space:pre-wrap;background:#f4f7f4;padding:12px;border-radius:10px';form.append(parts);
 form.append(select('Parts catalog / purchasing review',[
 ['needs_review','Needs parts review'],['matched','Matched to parts list — confirmed manually'],['new_part_needed','New catalog part needed'],['hold','Hold parts pricing for later'],['none_specified','No parts specified']],item.parts_review,v=>{item.parts_review=v}));
 form.append(select('Freight review',[
 ['not_assessed','Needs freight decision'],['required','Freight required — price in estimator'],['not_required','No freight needed'],['hold','Freight held for later']],item.freight_review,v=>{item.freight_review=v}));
 // Search the existing PDS Parts List. Matching is a suggestion, not a price authorization.
 const partsSearch=h('div');partsSearch.style.cssText='display:grid;gap:7px;border:1px solid #e1e8e2;padding:12px;border-radius:10px';
 partsSearch.append(h('strong','Search saved PDS Parts List'));
 const selectionStatus=h('small');selectionStatus.style.color='#53655b';
 const selectedHost=h('div');selectedHost.style.cssText='display:grid;gap:7px';
 const selectedPartsView=()=>{
   selectedHost.replaceChildren();
   for(const part of item.selected_parts){
     const line=h('div');line.style.cssText='display:flex;align-items:center;gap:8px;flex-wrap:wrap';
     line.append(h('span',part.part_number));
     const qty=h('input');qty.type='number';qty.min='1';qty.max='1000';qty.step='1';qty.value=part.quantity;
     qty.className='input';qty.style.width='90px';qty.setAttribute('aria-label','Quantity for '+part.part_number);
     qty.oninput=()=>{part.quantity=Number(qty.value)};
     const remove=h('button','Remove','btn');remove.onclick=()=>{
       item.selected_parts=item.selected_parts.filter(p=>p!==part);selectedPartsView();
       if(!item.selected_parts.length)item.parts_review='needs_review';
     };
     line.append(h('span','Qty'),qty,remove);selectedHost.append(line);
   }
   selectionStatus.textContent=item.selected_parts.length+' catalog part(s) selected; no prices imported';
 };
 selectedPartsView();
 const lookup=h('input');lookup.className='input';lookup.placeholder='Part number or description';
 const matches=h('div');matches.style.cssText='display:grid;gap:6px';
 const findParts=h('button','Find matching parts','btn');findParts.onclick=async()=>{
   const query=lookup.value.trim();if(query.length<2){matches.textContent='Enter at least two characters.';return}
   findParts.disabled=true;matches.textContent='Searching saved PDS parts…';
   try{
     const response=await fetch('/data/parts?q='+encodeURIComponent(query)+'&limit=12',{credentials:'same-origin'});
     if(!response.ok)throw Error('Parts list unavailable');
     const data=await response.json();matches.replaceChildren();
     const list=Array.isArray(data.items)?data.items:[];
     if(!list.length)matches.append(h('small','No matching saved part. Select “New catalog part needed” or “Hold” until the part is verified.'));
     for(const part of list.slice(0,12)){
       const number=String(part.Item||part.item||part.part_number||'').slice(0,90);
       const desc=String(part.Description||part.description||'').slice(0,160);
       const price=Number(part.Price ?? part.price);
       const row=h('button',[number,desc,Number.isFinite(price)?'Catalog price $'+price.toFixed(2):'Price unverified'].filter(Boolean).join(' · '),'btn');
       row.style.textAlign='left';row.onclick=()=>{
         if(!number){announce('Part has no catalog number; do not select it.');return}
         if(item.selected_parts.some(p=>p.part_number.toLowerCase()===number.toLowerCase()))return;
         item.selected_parts.push({part_number:number,quantity:1});
         item.parts_review='matched';
         selectionStatus.textContent=`${item.selected_parts.length} selected catalog part(s). Verify quantity and price in the estimator.`;
         selectedPartsView();
         for(const ctl of form.querySelectorAll('select')){
           if([...ctl.options].some(o=>o.value==='matched'))ctl.value='matched';
         }
       };matches.append(row)
     }
   }catch(error){matches.textContent='Could not search Parts List: '+(error.message||error)}finally{findParts.disabled=false}
 };
 const partIntake=h('button','Research / Add a new PDS part','btn');
 partIntake.type='button';partIntake.onclick=()=>document.dispatchEvent(new CustomEvent('moses-open-part-intake',
   {detail:{query:lookup.value.trim()||item.parts_required||''}}));
 partsSearch.append(selectedHost,selectionStatus,lookup,findParts,matches,partIntake);form.append(partsSearch);

 const noteField=field('Office instructions / missing pricing',item.review_note,v=>{item.review_note=v},'textarea');noteField.querySelector('textarea').dataset.reviewNote='true';form.append(noteField);
 const actions=h('div');actions.style.cssText='display:flex;gap:8px;flex-wrap:wrap';const result=h('small');result.setAttribute('role','status');
 const save=h('button','Save Changes','btn');const approve=h('button','Approve for Estimator','btn btn-orange');const decline=h('button','Decline','btn');
 const busy=x=>{for(const b of [save,approve,decline])b.disabled=x};
 save.onclick=async()=>{busy(true);try{const reply=await request('/'+encodeURIComponent(item.id),'PUT',{version:item.version,scope:item.scope,parts_review:item.parts_review,freight_review:item.freight_review,review_note:item.review_note,selected_parts:item.selected_parts});Object.assign(item,reply.item);result.textContent='Changes saved to Moses Drafts.';await render()}catch(e){result.textContent=e.message}finally{busy(false)}};
 for(const [button,approved] of [[approve,true],[decline,false]])button.onclick=async()=>{if(!window.confirm(approved?'Approve this review ticket for the PDS estimator? This does NOT issue or send an estimate.':'Decline this review ticket?'))return;busy(true);try{
  // Save edited fields before decision. A failed save never approves stale data.
  if(item.state==='pending_review'&&(item.scope!==original.scope||item.parts_review!==original.parts_review||item.freight_review!==original.freight_review||item.review_note!==original.review_note||JSON.stringify(item.selected_parts)!==JSON.stringify(original.selected_parts||[]))){
    const saved=await request('/'+encodeURIComponent(item.id),'PUT',{version:item.version,scope:item.scope,parts_review:item.parts_review,freight_review:item.freight_review,review_note:item.review_note,selected_parts:item.selected_parts});Object.assign(item,saved.item);
  }
  const reply=await request('/'+encodeURIComponent(item.id)+'/decide','POST',{version:item.version,approve:approved});result.textContent=approved?'Approved for estimator. No document issued or emailed.':'Draft declined and retained for audit.';Object.assign(item,reply.item);backdrop.remove();await render();
 }catch(e){result.textContent=e.message}finally{busy(false)}};
 actions.append(save,approve,decline);
 const reopen=h('button','Reopen','btn');reopen.onclick=async()=>{reopen.disabled=true;try{await request('/'+encodeURIComponent(item.id)+'/reopen','POST',{version:item.version});backdrop.remove();await render()}catch(e){result.textContent=e.message}finally{reopen.disabled=false}};
 const remove=h('button','Remove','btn');remove.onclick=async()=>{if(!window.confirm('Remove this draft from the list? Its audit history is kept.'))return;remove.disabled=true;try{await request('/'+encodeURIComponent(item.id)+'/archive','POST',{version:item.version});backdrop.remove();await render()}catch(e){result.textContent=e.message}finally{remove.disabled=false}};
 if(item.state!=='pending_review'){for(const b of [save,approve,decline])b.hidden=true;actions.append(reopen)}
 actions.append(remove);form.append(actions,result);
 dialog.append(form);backdrop.append(dialog);backdrop.addEventListener('dblclick',e=>{if(e.target===backdrop)backdrop.remove()});document.body.append(backdrop);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();
