/* Moses action center for the existing workspace assistant (not a second chat).
   Every card is sourced from the authenticated, read-only server endpoint. */
(() => {
  'use strict';
  const q = (selector, root = document) => root.querySelector(selector);
  const text = (tag, content, className = '') => {
    const node = document.createElement(tag);
    node.textContent = String(content == null ? '' : content);
    if (className) node.className = className;
    return node;
  };
  const request = async (url) => {
    const response = await fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(String(body.detail || `HTTP ${response.status}`));
    return body;
  };
  let lastWorkspace = '';
  let count = 0;
  function install() {
    const panel = document.getElementById('workspaceMosesPanel');
    if (!panel || q('#mosesActionCenterBtn', panel)) return;
    const header = panel.firstElementChild;
    if (!header) return;
    const button = text('button', 'Action Center', 'btn');
    button.type = 'button';
    button.id = 'mosesActionCenterBtn';
    button.setAttribute('aria-label', 'Moses outstanding actions from saved workspace records');
    // Match the clean Moses Job Flow surface without changing the chat or backend.
    if (!document.getElementById('mosesActionCenterStyle')) {
      const stylesheet = document.createElement('style');
      stylesheet.id = 'mosesActionCenterStyle';
      stylesheet.textContent = `
        .moses-chat-shell.moses-action-view:not(.moses-chat-expanded){
          width:min(1060px,calc(100vw - 28px))!important;right:50%!important;transform:translateX(50%)!important;bottom:14px!important;
          height:min(88dvh,880px)!important;max-height:calc(100dvh - 28px)!important;
          border-radius:17px!important
        }
        #mosesActionCenterArea{background:#fff!important;padding:14px 16px 20px!important}
        .moses-center-toolbar{display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap}
        .moses-center-tabs{display:flex;gap:8px;flex-wrap:wrap;padding:4px 0 12px;
          border-bottom:1px solid #e7ebee;position:sticky;top:0;background:#fff;z-index:1}
        .moses-center-tabs button{white-space:nowrap;font-weight:700}
        .moses-center-search{width:100%;min-height:42px;border:1px solid #d9e2e8;border-radius:12px;
          box-sizing:border-box;padding:10px 13px;background:#fff;font:inherit}
        .moses-center-group{display:grid;align-content:start;gap:10px}
        .moses-center-group[hidden]{display:none!important}
        .moses-center-card[hidden]{display:none!important}
        .moses-center-card{display:grid;gap:8px;border:1px solid #dce3e9;border-radius:12px;padding:12px;
          background:#fff;min-width:0}
        .moses-center-card strong{font-size:14px}
        .moses-center-card small{color:#64707d;font-size:12px;overflow-wrap:anywhere}
        .moses-center-actions{display:flex;flex-wrap:wrap;gap:7px;align-items:center}
        .moses-center-secondary{padding-top:5px;border-top:1px solid #f0f2f5}
        .moses-center-secondary .btn{font-size:12px;min-height:32px}
        .moses-center-empty{padding:16px;color:#687683;font-size:13px}
        @media(max-width:640px){.moses-chat-shell.moses-action-view:not(.moses-chat-expanded){
          inset:8px!important;width:auto!important;transform:none!important;height:calc(100dvh - 16px)!important;max-height:none!important;
          border-radius:16px!important}#mosesActionCenterArea{padding:10px 12px 18px!important}}
      `;
      document.head.append(stylesheet);
    }
    const area = document.createElement('section');
    area.id = 'mosesActionCenterArea';
    area.hidden = true;
    area.style.cssText = 'display:none;gap:10px;padding:12px 18px;margin:0;min-height:0;overflow-y:auto;overscroll-behavior:contain;border-top:1px solid #e1e5e9';
    const status = text('small', '');
    status.setAttribute('role', 'status');
    let activeTab = 'work';
    const toolbar = document.createElement('div');toolbar.className='moses-center-toolbar';
    const heading = text('strong', 'Action Center');
    const refresh = text('button', 'Refresh', 'btn');refresh.type = 'button';
    toolbar.append(heading,refresh);
    const tabs = document.createElement('nav');tabs.className='moses-center-tabs';
    tabs.setAttribute('aria-label','Moses action queues');
    const search = document.createElement('input');search.className='moses-center-search';
    search.type='search';search.placeholder='Search customer, job # or action';
    search.setAttribute('aria-label','Search Moses actions');
    status.style.cssText='display:block;min-height:15px;color:#687683;font-size:12px';
    const contents = document.createElement('div');contents.style.cssText='display:grid;gap:10px';
    area.append(toolbar,tabs,search,status,contents);
    const selectTab = (key) => {
      activeTab=key;search.value='';
      for(const group of contents.children) group.hidden=group.dataset.mosesTab!==activeTab;
      for(const tab of tabs.children){
        const selected=tab.dataset.mosesTab===activeTab;
        tab.className=selected?'btn btn-orange':'btn';
        tab.setAttribute('aria-pressed',String(selected));
      }
    };
    const filterCards=()=>{
      const value=search.value.trim().toLowerCase();
      for(const card of contents.querySelectorAll('.moses-center-card')){
        card.hidden=!!value&&!String(card.dataset.mosesSearch||'').includes(value);
      }
    };
    search.addEventListener('input',filterCards);
    const renderCards = (source, title, actionType) => {
      const section = document.createElement('section');section.className='moses-center-group';
      section.dataset.mosesTab=actionType;
      const available = source && source.available === true;
      const total = available ? source.count : null;
      const head=document.createElement('div');head.className='moses-center-toolbar';
      head.append(text('strong', title+' ('+(total == null?'—':total)+')'));
      if(actionType==='work'){
        const all=text('button','Open Full Job Flow','btn btn-orange');all.type='button';
        all.onclick=()=>document.dispatchEvent(new CustomEvent('moses-open-pds-job-flow'));
        head.append(all);
      }
      section.append(head);
      const inside=document.createElement('div');inside.style.cssText='display:grid;gap:10px';section.append(inside);
      if (!available) {
        inside.append(text('small', String(source?.note || 'Unavailable.'), 'moses-center-empty'));
      } else if (!total) {
        inside.append(text('small', 'No items.', 'moses-center-empty'));
      }
      for (const item of (Array.isArray(source?.items) ? source.items : []).slice(0, 12)) {
        const card = document.createElement('article');
        card.className='moses-center-card';
        card.dataset.mosesSearch=[item.title,item.customer,item.job_number,item.kind,item.status,item.state].filter(Boolean).join(' ').toLowerCase();
        card.append(text('strong', item.customer || item.title || item.kind || 'Saved action'));
        card.append(text('small', [item.job_number && `Job #${item.job_number}`,
          item.status || item.state,item.customer ? item.title : ''].filter(Boolean).join(' · ')));
        if (item.next_step && actionType === 'delivery') card.append(text('small',item.next_step));
        if (actionType === 'draft' && item.draft_id) {
          const inspect = text('button', 'Review draft', 'btn');
          inspect.type = 'button';
          inspect.onclick = async () => {
            inspect.disabled = true;
            try {
              const result = await request('/moses-action-center/pds/drafts/' + encodeURIComponent(item.draft_id));
              const detail = text('small', [result.draft?.scope, result.draft?.parts_required,
                result.next_step].filter(Boolean).join('\n\n'));
              detail.style.whiteSpace = 'pre-wrap';
              card.querySelector('[data-moses-draft-detail]')?.remove();
              detail.dataset.mosesDraftDetail = '1';
              card.append(detail);
              const open = document.getElementById('mosesDraftsLaunch');
              if (open && !open.hidden) {
                const go = text('button', 'Open Moses Drafts workspace', 'btn');
                go.type = 'button';
                go.onclick = () => open.click();
                card.append(go);
              }
            } catch (err) {
              card.append(text('small', 'Saved draft cannot be verified: ' + err.message));
            } finally { inspect.disabled = false; }
          };
          card.append(inspect);
        }
        if (actionType === 'work' && item.record_id && (document.body.dataset.platform || '') === 'pds') {
          const secondary=document.createElement('div');secondary.className='moses-center-actions moses-center-secondary';
          const inspect = text('button', 'Inspect', 'btn');
          inspect.type = 'button';
          inspect.onclick = async () => {
            inspect.disabled = true;
            try {
              const result = await request('/moses-action-center/pds/jobs/' + encodeURIComponent(item.record_id) + '/context');
              if (result.workspace !== 'pds' || result.job?.id !== item.record_id) throw new Error('Job identity mismatch');
              const summary = text('small', [
                `${result.job.customer || 'Saved job'} · #${result.job.job_number || '—'} · ${result.job.status || '—'}`,
                `Linked documents: ${result.documents.available ? result.documents.count : 'unavailable'}`,
                `Saved Moses drafts: ${result.moses_drafts.available ? result.moses_drafts.count : 'unavailable'}`,
                ...(result.next_steps || [])
              ].join('\n'));
              summary.style.whiteSpace = 'pre-wrap';
              card.querySelector('[data-moses-job-context]')?.remove();
              summary.dataset.mosesJobContext = '1';
              card.append(summary);
            } catch (err) {
              status.textContent = 'Cannot verify PDS job context: ' + err.message;
            } finally { inspect.disabled = false; }
          };
          secondary.append(inspect);
          const buttons=document.createElement('div');buttons.className='moses-center-actions';
          const view=text('button','View Job','btn');view.type='button';
          view.onclick=()=>document.dispatchEvent(new CustomEvent('moses-open-pds-job',{detail:{job_id:item.record_id}}));
          buttons.append(view);
          const statusLabel=String(item.status||'').toLowerCase();
          const isQuote=/quote|to be quoted/.test(statusLabel) || item.kind==='needs_quote';
          const isInvoice=/invoice|complete|done/.test(statusLabel);
          const needsParts=item.kind==='parts_on_order';
          const run=(action,label,primary=false)=>{
            const control=text('button',label,primary?'btn btn-orange':'btn');control.type='button';
            control.onclick=()=>document.dispatchEvent(new CustomEvent('moses-open-pds-jobflow-action',
              {detail:{job_id:item.record_id,action}}));
            buttons.append(control);
          };
          if(isQuote||needsParts)run('supplier','Request Supplier Quote');
          if(isQuote)run('estimate','Estimate',true);
          if(isInvoice)run('invoice','Invoice',true);
          const ask=text('button','Ask Moses','btn');ask.type='button';
          ask.onclick=()=>{
            const input=q('#mosesChatMessage',panel);if(!input){status.textContent='Moses chat unavailable.';return;}
            input.value='Review PDS job '+(item.job_number||item.record_id)+' and suggest the next authorized steps from its saved records. Do not save or send anything without approval.';
            area.hidden=true;area.style.display='none';panel.classList.remove('moses-action-view');button.textContent='Action Center';input.focus();
          };buttons.append(ask);
          if (isQuote) {
            const split = text('button','Separate estimate scopes','btn');split.type='button';
            split.onclick=async()=>{
              split.disabled=true;
              try {
                const data=await request('/moses-action-center/pds/jobs/'+encodeURIComponent(item.record_id)+'/estimate-scopes');
                const old=card.querySelector('[data-moses-scopes-editor]');if(old)old.remove();
                const editor=document.createElement('section');editor.dataset.mosesScopesEditor='1';
                editor.style.cssText='display:grid;gap:10px;padding:10px;border:1px solid #dbe4ea;border-radius:10px';
                editor.append(text('strong','Review separate estimate scopes'));
                editor.append(text('small','Each scope is an unpriced Moses draft. No estimate will be issued. Select only the recommendations that need separate quotes.'));
                const rows=document.createElement('div');rows.style.cssText='display:grid;gap:10px';
                editor.append(rows);
                const addRow=(source,title='',description='')=>{
                  const section=document.createElement('div');section.style.cssText='display:grid;gap:5px;padding:8px;border-top:1px solid #e3e7eb';
                  section.dataset.sourceIndex=String(source.source_form_index);
                  section.append(text('small','Completion Form #'+source.source_form_number+' · '+(source.door_location||'Location not recorded')));
                  const heading=document.createElement('input');heading.placeholder='Scope title / opening';heading.maxLength=140;
                  heading.value=title;heading.setAttribute('aria-label','Estimate scope title');
                  const body=document.createElement('textarea');body.rows=3;body.maxLength=3000;body.placeholder='Describe exactly which work belongs in this estimate';
                  body.value=description;body.setAttribute('aria-label','Estimate scope description');
                  const remove=text('button','Remove this scope','btn');remove.type='button';remove.onclick=()=>section.remove();
                  const another=text('button','Add another scope from this form','btn');another.type='button';
                  another.onclick=()=>addRow(source,source.door_location||'Separate opening','');
                  section.append(heading,body,remove,another);rows.append(section);
                };
                for(const source of data.proposed_scopes||[]){
                  const details=source.scope||{};
                  addRow(source,source.door_location||('Completion Form #'+source.source_form_number),
                    [details.recommendations,details.additional_recommendations,details.parts_required].filter(Boolean).join('\n'));
                }
                const save=text('button','Save separate Moses review drafts','btn');save.type='button';
                save.onclick=async()=>{
                  const scopes=[...rows.children].map(row=>({source_form_index:Number(row.dataset.sourceIndex),
                    title:row.querySelector('input')?.value.trim()||'',scope:row.querySelector('textarea')?.value.trim()||''}));
                  if(!scopes.length){status.textContent='Select at least one source scope.';return;}
                  if(!window.confirm('Save '+scopes.length+' separate unpriced draft reviews for this job?'))return;
                  save.disabled=true;
                  try{
                    const response=await fetch('/moses-drafts/prepare-job-scopes',{method:'POST',credentials:'same-origin',
                      headers:{'Content-Type':'application/json'},body:JSON.stringify({record_id:item.record_id,scopes})});
                    const result=await response.json().catch(()=>({}));
                    if(!response.ok)throw new Error(result.detail||'Unable to save scopes');
                    status.textContent=result.created+' new scope reviews saved. Open Moses Drafts for separate approvals.';
                    editor.remove();
                  }catch(error){status.textContent='Scope drafts not saved: '+error.message;save.disabled=false;}
                };
                editor.append(save);card.append(editor);
              }catch(error){status.textContent='Cannot load saved completion scopes: '+error.message;}
              finally{split.disabled=false;}
            };secondary.append(split);
          }
          card.append(buttons,secondary);
        }
        if (actionType === 'approval') {
          const open = text('button', 'Review existing approvals', 'btn');
          open.type = 'button';
          open.onclick = () => {
            const prior = Array.from(panel.querySelectorAll('button')).find(b => b.textContent.trim() === 'Review pending Moses actions');
            if (prior) {
              area.hidden=true;area.style.display='none';panel.classList.remove('moses-action-view');
              button.textContent='Action Center';prior.click();
            } else status.textContent = 'Approval interface unavailable. No record changed.';
          };
          card.append(open);
        }
        inside.append(card);
      }
      if(available && total>12)inside.append(text('small',actionType==='work'?'Showing 12 of '+total+'. Open Full Job Flow for the rest.':'Showing the first 12 of '+total+' records.','moses-center-empty'));
      contents.append(section);
    };
    const load = async () => {
      const workspace = document.body.dataset.platform || '';
      const sequence = ++count;
      status.textContent = 'Reading saved business records…';
      refresh.disabled = true;
      try {
        const data = await request('/moses-action-center/overview');
        if (sequence !== count || workspace !== (document.body.dataset.platform || '') || data.workspace !== workspace) {
          status.textContent = 'Workspace changed. Refresh to read the active workspace.';
          return;
        }
        lastWorkspace = workspace;
        contents.replaceChildren();
        if (workspace === 'pds') {
          // Separate human-approved SMS decisions. No click can send without a
          // fresh confirmation, server-side session, active consent, and provider gate.
          try {
            const sms = await request('/moses-action-center/pds/sms/proposals');
            const rows = Array.isArray(sms.proposals) ? sms.proposals : [];
            const section = document.createElement('section');section.className='moses-center-group';
            section.dataset.mosesTab='sms';
            section.append(text('strong','PDS text approvals ('+rows.length+')'));
            const inside = document.createElement('div');
            inside.style.cssText='display:grid;gap:10px;padding:12px';
            if (!rows.length) inside.append(text('small','No text messages awaiting approval.'));
            for (const entry of rows) {
              const card = document.createElement('article');
              card.className='moses-center-card';
              card.dataset.mosesSearch=[entry.job_id,entry.status,entry.phone].filter(Boolean).join(' ').toLowerCase();
              card.append(text('strong', 'Job ' + (entry.job_id || '') + ' · ' + (entry.status || '')));
              card.append(text('small', entry.phone || ''));
              const body = text('div', entry.message || '');body.style.whiteSpace='pre-wrap';card.append(body);
              if (entry.status === 'pending') {
                const actions = document.createElement('div');actions.style.cssText='display:flex;gap:8px';
                for (const approved of [true,false]) {
                  const act = text('button',approved?'Approve & send text':'Decline','btn');act.type='button';
                  act.onclick = async () => {
                    if (!window.confirm(approved ? 'Send this exact service text to '+entry.phone+'?' : 'Decline this text request?')) return;
                    act.disabled=true;
                    try {
                      const response=await fetch('/moses-action-center/pds/sms/proposals/'+encodeURIComponent(entry.id)+'/decision',{
                        method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({approve:approved})});
                      const result=await response.json().catch(()=>({}));
                      if(!response.ok)throw new Error(result.detail||'Request failed');
                      status.textContent=approved?'Text submitted to Twilio; delivery not yet confirmed.':'Text declined.';
                      await load();
                    } catch (error) { status.textContent='SMS decision not confirmed: '+error.message;act.disabled=false; }
                  };actions.append(act);
                }card.append(actions);
              } else {card.append(text('small','Requires provider log reconciliation; no automatic retry.'));}
              inside.append(card);
            }
            section.append(inside);contents.append(section);
          } catch (error) {
            const section=document.createElement('section');section.className='moses-center-group';
            section.dataset.mosesTab='sms';
            section.append(text('small','Text approval inbox unavailable: '+error.message,'moses-center-empty'));
            contents.append(section);
          }
        }
        if (workspace === 'pds') renderCards(data.drafts, 'Saved drafts', 'draft');
        renderCards(data.approvals, 'Approvals', 'approval');
        if (workspace === 'pds') renderCards(data.work, 'PDS jobs needing attention', 'work');
        renderCards(data.delivery, 'Delivery issues', 'delivery');
        const labels={work:'Jobs',draft:'Drafts',approval:'Approvals',delivery:'Delivery',sms:'Texts'};
        const counts={work:data.work?.count,draft:data.drafts?.count,
          approval:data.approvals?.count,delivery:data.delivery?.count,
          sms:contents.querySelector('[data-moses-tab="sms"]')?.querySelectorAll('.moses-center-card').length||0};
        const kinds=workspace==='pds'?['work','draft','approval','delivery','sms']:['approval','delivery'];
        tabs.replaceChildren();
        for(const kind of kinds){
          const total=counts[kind];const tab=text('button',labels[kind]+' ('+(total==null?'—':total)+')','btn');
          tab.type='button';tab.dataset.mosesTab=kind;tab.onclick=()=>selectTab(kind);tabs.append(tab);
        }
        if(!kinds.includes(activeTab))activeTab=kinds[0];
        selectTab(activeTab);
        status.textContent = '';
      } catch (err) {
        contents.replaceChildren();
        status.textContent = 'Could not verify action center: ' + err.message + '. No records were changed.';
      } finally { refresh.disabled = false; }
    };
    refresh.onclick = load;
    button.onclick = async () => {
      area.hidden = !area.hidden;
      area.style.display = area.hidden ? 'none' : 'grid';
      panel.classList.toggle('moses-action-view', !area.hidden);
      button.textContent = area.hidden ? 'Action Center' : 'Back to chat';
      if (!area.hidden) await load();
    };
    const headerActions=header.querySelector('.moses-header-actions');
    if(headerActions)headerActions.prepend(button);
    else header.append(button);
    header.after(area);
    // Always refresh when reopening after switching business platforms.
    const onClick = (ev) => {
      if (ev.target?.id === 'workspaceMosesBubble' && lastWorkspace !== (document.body.dataset.platform || '')) {
        area.hidden = true; area.style.display = 'none'; panel.classList.remove('moses-action-view');
        button.textContent='Action Center';contents.replaceChildren();tabs.replaceChildren();
        activeTab=(document.body.dataset.platform||'')==='pds'?'work':'approval';
      }
    };
    document.addEventListener('click', onClick);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
  // The existing app creates the Moses panel lazily after login/workspace render.
  const observer = new MutationObserver(() => {
    if (document.getElementById('workspaceMosesPanel') && !document.getElementById('mosesActionCenterBtn')) install();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
