/* Moses document difference reviewer. Exact server-record target, manual per-field checkboxes. */
(function(root){
  'use strict';
  const make=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el};
  const labels={estimate_number:'Estimate number',po_number:'PO number',invoice_number:'Invoice number',job_notes:'Job notes',office_notes:'Office notes'};
  async function call(path,body){
    const res=await fetch('/dispatch-ai/'+path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data=await res.json();if(!res.ok)throw new Error(data.detail||'PDS document review failed');return data;
  }
  async function mount({host,fields,candidate}){
    if(!host||!candidate?.matched_job_number||!candidate?.job_number)return;
    host.querySelector('[data-moses-change-review]')?.remove();
    const box=make('section');box.dataset.mosesChangeReview='true';box.style.cssText='display:grid;gap:9px;border:1px solid #ccd5df;padding:14px;border-radius:12px;margin:10px 0;background:#fff';
    box.append(make('strong','Review changes to existing PDS ticket'));
    const info=make('small','Only selected fields will change. Customer, address, status, and job number are protected.');box.append(info);
    const status=make('div','Comparing with the current saved ticket…');status.setAttribute('role','status');box.append(status);
    host.append(box);
    try {
      let report=await call('compare-existing',{job_number:candidate.job_number,fields});
      if(!report.changes?.length){status.textContent='No new document values to apply. The saved ticket remains unchanged.';return;}
      status.textContent='Select the fields you want applied. Review any values that will replace existing data.';
      const selections=[];
      for(const change of report.changes){
        const row=make('label');row.style.cssText='display:grid;gap:6px;border:1px solid #e3e8ef;border-radius:9px;padding:10px';
        const top=make('span');const check=make('input');check.type='checkbox';check.style.marginRight='8px';top.append(check,document.createTextNode(labels[change.field]||change.field));row.append(top);
        if(change.would_replace_existing)row.append(make('small','This will REPLACE an existing saved value.'));
        const old=make('div','Saved: '+(change.saved_value||'(blank)'));old.style.cssText='white-space:pre-wrap;max-height:130px;overflow:auto;color:#667085';row.append(old);
        row.append(make('small','Document suggestion (editable before applying):'));
        const proposed=make('textarea');proposed.value=change.suggested_value;proposed.rows=change.field.endsWith('notes')?4:2;proposed.className='input';proposed.maxLength=change.field.endsWith('notes')?4000:90;row.append(proposed);
        box.append(row);selections.push({field:change.field,check,proposed});
      }
      const actions=make('div');actions.style.cssText='display:flex;gap:10px;flex-wrap:wrap';
      const apply=make('button','Apply selected changes');apply.type='button';apply.className='btn btn-orange';
      const cancel=make('button','Close comparison');cancel.type='button';cancel.className='btn';cancel.onclick=()=>box.remove();actions.append(apply,cancel);box.append(actions);
      apply.onclick=async()=>{
        const changes=Object.fromEntries(selections.filter(s=>s.check.checked).map(s=>[s.field,s.proposed.value.trim()]));
        if(!Object.keys(changes).length){status.textContent='Select at least one field first.';return;}
        if(!window.confirm('Apply '+Object.keys(changes).length+' selected field(s) to saved PDS job '+report.job_number+'? Changes may replace existing values.'))return;
        apply.disabled=true;
        try{
          const result=await call('apply-existing',{job_number:report.job_number,expected_version:report.version,changes,confirmed:true});
          status.textContent=result.updated?'Saved and verified '+result.fields_changed.join(', ')+'.':'No change needed; values already saved.';
          for(const s of selections){s.check.disabled=true;s.proposed.disabled=true;}apply.disabled=true;
        }catch(e){status.textContent='Nothing confirmed saved: '+(e.message||e)+'. Refresh the document review before retrying.';apply.disabled=false;}
      };
    }catch(e){status.textContent='Unable to compare safely: '+(e.message||e)+'. Open the original ticket to review it.';}
  }
  root.MosesDocumentChanges={mount};
})(typeof window!=='undefined'?window:globalThis);
