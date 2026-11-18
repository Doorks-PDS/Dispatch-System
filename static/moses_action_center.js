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
    const area = document.createElement('section');
    area.id = 'mosesActionCenterArea';
    area.hidden = true;
    area.style.cssText = 'display:none;gap:10px;padding:12px 18px;margin:0;min-height:0;overflow-y:auto;overscroll-behavior:contain;border-top:1px solid #e1e5e9';
    const status = text('small', '');
    status.setAttribute('role', 'status');
    area.append(status);
    const refresh = text('button', '↻ Refresh', 'btn');
    refresh.type = 'button';
    const contents = document.createElement('div');
    contents.style.cssText = 'display:grid;gap:10px';
    area.append(refresh, contents);
    const renderCards = (source, title, actionType) => {
      const section = document.createElement('details');
      const tones={draft:['#eaf2ff','#3b64a0'],approval:['#fff1de','#aa6813'],work:['#ebf4ed','#397b50'],delivery:['#fff0ef','#af4a42']};
      const [surface,accent]=tones[actionType]||['#f4f5f7','#536273'];
      section.style.cssText='border:1px solid #dfe6e9;border-left:3px solid '+accent+';border-radius:11px;padding:0;overflow:hidden;background:#fff';
      const available = source && source.available === true;
      const total = available ? source.count : null;
      const name = text('summary', title + ' (' + (total == null ? '—' : total) + ')');
      name.style.cssText='padding:12px 13px;cursor:pointer;font-weight:700;background:'+surface+';color:'+accent;
      section.append(name);
      const inside=document.createElement('div');inside.style.cssText='display:grid;gap:8px;padding:9px 12px';section.append(inside);
      if (!available) {
        inside.append(text('small', String(source?.note || 'Unavailable.')));
      } else if (!total) {
        inside.append(text('small', 'No items.'));
      }
      for (const item of (Array.isArray(source?.items) ? source.items : []).slice(0, 12)) {
        const card = document.createElement('article');
        card.style.cssText = 'display:grid;gap:5px;border-top:1px solid #eef1f5;padding-top:8px';
        card.append(text('strong', item.title || item.customer || item.kind || 'Saved action'));
        card.append(text('small', [item.customer, item.job_number && `Job #${item.job_number}`,
          item.status || item.state].filter(Boolean).join(' · ')));
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
          const inspect = text('button', 'View details', 'btn');
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
          card.append(inspect);
          const buttons=document.createElement('div');buttons.style.cssText='display:flex;gap:6px;flex-wrap:wrap';
          const view=text('button','View Job','btn');view.type='button';
          view.onclick=()=>document.dispatchEvent(new CustomEvent('moses-open-pds-job',{detail:{job_id:item.record_id}}));
          buttons.append(view);
          const statusLabel=String(item.status||'').toLowerCase();
          const isInvoice=/invoice|complete|done/.test(statusLabel)&&!/quote/.test(statusLabel);
          const task=text('button',isInvoice?'Prepare invoice':'Prepare estimate','btn');task.type='button';
          task.onclick=()=>{
            const prompt='Review PDS job '+(item.job_number||item.record_id)+' and '+(isInvoice?'prepare a draft invoice':'prepare an estimate draft')+' from verified saved job records and forms. Show anything missing and request approval before consequential changes.';
            const input=q('#mosesChatMessage',panel);if(!input){status.textContent='Moses message input unavailable.';return;}
            input.value=prompt;area.hidden=true;area.style.display='none';panel.classList.remove('moses-action-view');input.focus();
            // User explicitly chose an action; never auto-execute financial changes.
          };buttons.append(task);
          if (!isInvoice) {
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
            };buttons.append(split);
          }
          card.append(buttons);
        }
        if (actionType === 'approval') {
          const open = text('button', 'Review existing approvals', 'btn');
          open.type = 'button';
          open.onclick = () => {
            const prior = Array.from(panel.querySelectorAll('button')).find(b => b.textContent.trim() === 'Review pending Moses actions');
            if (prior) prior.click();
            else status.textContent = 'Approval interface unavailable. No record changed.';
          };
          card.append(open);
        }
        inside.append(card);
      }
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
            const section = document.createElement('details');
            const heading = text('summary', 'PDS text approvals (' + rows.length + ')');
            heading.style.cssText='padding:12px;font-weight:700;cursor:pointer;background:#fff1de';
            section.style.cssText='border:1px solid #e3e7eb;border-radius:12px;overflow:hidden';
            section.append(heading);
            const inside = document.createElement('div');
            inside.style.cssText='display:grid;gap:10px;padding:12px';
            if (!rows.length) inside.append(text('small','No text messages awaiting approval.'));
            for (const entry of rows) {
              const card = document.createElement('article');
              card.style.cssText='display:grid;gap:8px;border-top:1px solid #e5e8eb;padding:10px 0';
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
          } catch (error) {status.textContent='SMS approval inbox unavailable: '+error.message;}
        }
        if (workspace === 'pds') renderCards(data.drafts, 'Moses draft reviews', 'draft');
        renderCards(data.approvals, 'Awaiting your approval', 'approval');
        if (workspace === 'pds') renderCards(data.work, 'PDS job follow-ups', 'work');
        renderCards(data.delivery, 'Verified delivery exceptions', 'delivery');
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
    header.insertBefore(button, header.lastElementChild);
    header.after(area);
    // Always refresh when reopening after switching business platforms.
    const onClick = (ev) => {
      if (ev.target?.id === 'workspaceMosesBubble' && lastWorkspace !== (document.body.dataset.platform || '')) {
        area.hidden = true; area.style.display = 'none'; panel.classList.remove('moses-action-view'); button.textContent='Action Center';contents.replaceChildren();
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
