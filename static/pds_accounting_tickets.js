/* PDS-only office ticket drawer. Existing stores and permissions remain authoritative. */
(()=>{'use strict';
 const dollars=v=>Number(v||0).toLocaleString('en-US',{style:'currency',currency:'USD'});
 const el=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;};
 const field=(parent,label,value)=>{const d=el('div','pds-accounting-field');d.append(el('strong','',label),el('span','',value===undefined||value===null||value===''?'—':value));parent.append(d);};
 const request=async(url,options)=>{const resp=await fetch(url,{credentials:'same-origin',...options});const body=await resp.json().catch(()=>({}));if(!resp.ok)throw Error(body.detail||`HTTP ${resp.status}`);return body;};
 const likely=(tx,receipts)=>{
   const amount=Number(tx.amount);if(!(amount>0))return[];
   const day=Date.parse(String(tx.date||'').slice(0,10)+'T12:00:00Z');
   return (receipts||[]).filter(r=>{
      if(!r||Math.abs(Number(r.amount)-amount)>0.01)return false;
      if(tx.card_last4&&r.card_last4&&String(tx.card_last4)!==String(r.card_last4))return false;
      const d=Date.parse(String(r.date||'').slice(0,10)+'T12:00:00Z');
      if(!Number.isNaN(day)&&!Number.isNaN(d)&&Math.abs(day-d)>5*86400000)return false;
      return true;
   }).slice(0,5);
 };
 function show(kind,record,receipts=[]){
   const prior=document.querySelector('.pds-accounting-overlay');if(prior)prior.remove();
   const overlay=el('div','overlay pds-accounting-overlay');const drawer=el('div','drawer pds-accounting-drawer');
   drawer.setAttribute('role','dialog');drawer.setAttribute('aria-modal','true');drawer.setAttribute('aria-label',kind==='statement'?'Statement ticket':'Receipt ticket');
   const header=el('div','drawer-hd'),title=el('h2','',kind==='statement'?'Statement Details':'Receipt Details');
   const close=el('button','drawer-close','×');close.type='button';close.setAttribute('aria-label','Close ticket');
   header.append(title,close);const content=el('div','drawer-bd');drawer.append(header,content);overlay.append(drawer);document.body.append(overlay);
   const dismiss=()=>overlay.remove();close.onclick=dismiss;overlay.addEventListener('dblclick',event=>{if(event.target===overlay)dismiss()});
   const summary=el('section','card pds-accounting-summary');content.append(summary);
   if(kind==='statement'){
      field(summary,'Issuer',record.issuer);field(summary,'Statement period',[record.period_start,record.period_end].filter(Boolean).join(' — '));
      field(summary,'Type',record.document_type);field(summary,'Notes',record.notes);
      const txs=Array.isArray(record.transactions)?record.transactions:[];
      const net=txs.filter(t=>!t.exclude_from_expenses).reduce((sum,t)=>sum+Number(t.amount||0),0);
      const stats=el('div','pds-accounting-metrics');
      field(stats,'Transactions',txs.length);field(stats,'Included net activity',dollars(net));
      field(stats,'Needs category',txs.filter(t=>!t.category||t.category==='Other').length);
      summary.append(stats);
      const label=el('h3','','Statement transactions & possible receipts');content.append(label);
      const note=el('p','hint','Review extracted items, categories, and transfers before using these totals. A possible receipt match is not a confirmed reconciliation. Receipts are NOT automatically counted twice.');content.append(note);
      const categories=['Uncategorized','Parts & Materials','Tools & Equipment','Fuel','Vehicle Maintenance','Office Supplies','Shipping & Freight','Meals','Travel','Stock / Inventory','Business & Licensing Fees','Other','Card Payment / Transfer','Refund / Credit','Personal / Nonbusiness'];
      const entries=el('div','pds-transaction-entries');content.append(entries);
      txs.forEach((tx,index)=>{
         const card=el('section','card pds-tx-row');entries.append(card);
         const top=el('div','pds-tx-heading');top.append(el('strong','',tx.vendor||'Unidentified transaction'),el('strong','',dollars(tx.amount)));card.append(top);
         field(card,'Date',tx.date);field(card,'Card',tx.card_last4?'•••• '+tx.card_last4:'—');field(card,'Reference',tx.receipt_number);field(card,'Employee',tx.employee);field(card,'Notes',tx.notes);
         const match=likely(tx,receipts);const matches=el('div','pds-tx-matches');matches.append(el('strong','',`Possible receipts: ${match.length}`));
         match.forEach(r=>{const link=el('a','',`${r.vendor||'Receipt'} · ${r.date||''} · ${dollars(r.amount)}`);link.href='/receipts/'+encodeURIComponent(r.id)+'/file';link.target='_blank';link.rel='noopener noreferrer';matches.append(link);const attach=el('button','btn','Link receipt');attach.type='button';attach.onclick=()=>save(r.id);matches.append(attach)});
         const linked=(receipts||[]).find(r=>r.id&&r.id===tx.matched_receipt_id);
         if(linked){matches.append(el('small','hint','Linked: '+String(linked.vendor||linked.id)));const detach=el('button','btn','Unlink receipt');detach.type='button';detach.onclick=()=>save('');matches.append(detach)}
         card.append(matches);
         const edit=el('div','pds-tx-controls');const selector=el('select','input');selector.setAttribute('aria-label','Transaction category');
         for(const val of [...new Set([tx.category||'Uncategorized',...categories])]){const option=el('option','',val);option.value=val;selector.append(option)}selector.value=tx.category||'Uncategorized';
         const exclLabel=el('label','pds-tx-check','Exclude from expense totals');const excluded=el('input');excluded.type='checkbox';excluded.checked=!!tx.exclude_from_expenses;exclLabel.prepend(excluded);
         const status=el('small','hint','');edit.append(selector,exclLabel,status);card.append(edit);
         const save=async(receiptId)=>{selector.disabled=excluded.disabled=true;status.textContent='Saving…';try{
           // Re-fetch the latest statement to avoid overwriting another editor's changes.
           const current=await request('/accounting/statements');const fresh=(current.items||[]).find(r=>r.id===record.id);
           if(!fresh||!Array.isArray(fresh.transactions)||fresh.transactions.length!==txs.length)throw Error('Statement changed; reopen ticket');
           const before=fresh.transactions[index];if(JSON.stringify(before)!==JSON.stringify(txs[index]))throw Error('Transaction was updated elsewhere; reopen ticket');
           if(receiptId && txs.some((row,j)=>j!==index&&row.matched_receipt_id===receiptId))throw Error('Receipt already linked to another charge in this statement');
           const changed=fresh.transactions.map((t,i)=>i===index?{...t,category:selector.value==='Uncategorized'?'':selector.value,exclude_from_expenses:excluded.checked,...(receiptId!==undefined?{matched_receipt_id:receiptId}:{} )}:t);
           await request('/accounting/statements/'+encodeURIComponent(record.id),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({...fresh,transactions:changed})});
           txs[index]={...changed[index]};status.textContent=receiptId!==undefined?'Link saved — reopen to review':'Saved';
         }catch(e){status.textContent='Not saved: '+(e.message||e);selector.value=tx.category||'Uncategorized';excluded.checked=!!tx.exclude_from_expenses}finally{selector.disabled=excluded.disabled=false;}};
         selector.onchange=save;excluded.onchange=save;
      });
      if(!txs.length)content.append(el('p','hint','No individual transactions were saved for this statement. Use the statement editor and Read with AI to extract and review charges from the original.'));
   }else{
      for(const [key,label] of [['vendor','Vendor'],['date','Date'],['amount','Amount'],['employee','Employee'],['category','Category'],['document_type','Document type'],['job_number','Linked job #'],['stock_reference','Stock reference'],['po_number','Purchase order #'],['receipt_number','Receipt #'],['card_last4','Card last four'],['notes','Notes'],['authorization_status','Authorization']]){
        const value=key==='amount'?dollars(record[key]):record[key];field(summary,label,value);
      }
   }
   const file=kind==='statement'&&record.attachment?'/accounting/statements/'+encodeURIComponent(record.id)+'/file':kind==='receipt'&&record.stored_file?'/receipts/'+encodeURIComponent(record.id)+'/file':'';
   if(file){const actions=el('div','pds-accounting-files');const a=el('a','btn','Download Original');a.href=file;a.target='_blank';a.rel='noopener noreferrer';actions.append(a);content.append(actions);
      const filename=String(record.original_filename||record.filename||record.attachment||record.stored_file||'');
      if(/\.(jpg|jpeg|png|webp)$/i.test(filename)){
        const image=el('img','pds-accounting-image');image.src=file+'?inline=1';image.alt='Original '+kind+' attachment';image.onerror=()=>image.remove();content.append(image);
      }
   }
 }
 async function jobReceipts(container,job){
   const number=String(job?.job_number||'').trim();if(!number)return;
   const host=el('section','card pds-job-linked-receipts');host.append(el('h3','','Receipts & packing slips'),el('p','hint','Files submitted for this job. Stock balances are not modified by attaching a receipt.'));
   container.append(host);
   try{const data=await request('/receipts');if(!host.isConnected)return;
     const rows=(data.items||[]).filter(r=>String(r.job_number||'').trim().toLowerCase()===number.toLowerCase());
     if(!rows.length){host.append(el('p','hint','No uploaded receipts or packing slips linked to this job.'));return;}
     rows.forEach(r=>{const line=el('div','pds-job-linked-item');line.append(el('span','',`${r.document_type||'Receipt'} · ${r.vendor||''} · ${r.date||''}`));const b=el('button','btn','View');b.type='button';b.onclick=()=>show('receipt',r,rows);line.append(b);host.append(line)})
   }catch(_){host.append(el('p','hint','Linked receipts require the appropriate signed-in permissions and, for office users, an unlocked Accounting Hub.'))}
 }
 window.PDSOfficeTickets={show,jobReceipts};
})();
