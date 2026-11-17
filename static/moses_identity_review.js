/* Moses PDS intake: explicit saved-record identity reconciliation.
   Does not create customers, addresses, jobs, or trust model output as identity. */
(function (root) {
  'use strict';
  const str = x => String(x == null ? '' : x).trim();
  const words = x => str(x).toLowerCase().replace(/&/g, ' and ')
    .replace(/\b(co|co\.|company|corporation|corp|incorporated|inc|llc|ltd)\b\.?/g, ' company ')
    .replace(/\bthe\b/g, ' ').replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
  const normStreet = x => str(x).toLowerCase().replace(/\b(avenue|ave\.?|street|st\.?|drive|dr\.?|road|rd\.?|boulevard|blvd\.?|lane|ln\.?)\b/g, m => ({avenue:'ave',street:'st',drive:'dr',road:'rd',boulevard:'blvd',lane:'ln'}[m.replace(/\.$/,'')] || m.replace(/\.$/,'')) )
    .replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
  function addressParts(x) {
    const v = str(x);
    const zip = (v.match(/\b\d{5}(?:-\d{4})?\b/) || [])[0] || '';
    const front = v.split(',')[0].replace(/\b(?:San Diego|La Jolla|Escondido|Carlsbad|Oceanside|Irvine)\b.*$/i, '').trim();
    return {street: normStreet(front), zip:zip.slice(0,5)};
  }
  function companyCandidates(name, records) {
    const key = words(name);
    if (!key) return [];
    const names = new Map();
    for (const row of (Array.isArray(records)?records:[])) {
      if (!row || typeof row !== 'object') continue;
      const label = str(row.company_name || row.name || row.customer_name);
      if (label && words(label) === key && !names.has(label.toLowerCase())) names.set(label.toLowerCase(), {value:label,label});
    }
    return Array.from(names.values());
  }
  function addressCandidates(address, records, customer) {
    const wanted = addressParts(address);
    if (!wanted.street || !/^\d+\s/.test(wanted.street)) return [];
    const matches = new Map();
    for(const row of (Array.isArray(records)?records:[])) {
      if(!row || typeof row!=='object') continue;
      const value = str(row.address || row.formatted_address || row.job_site_address);
      const parts = addressParts(value);
      if(!value || parts.street !== wanted.street || (wanted.zip && parts.zip && wanted.zip!==parts.zip))continue;
      const owner = str(row.company_name || row.customer || row.customer_name);
      if(customer && owner && words(owner)!==words(customer))continue;
      const key = normStreet(value);
      if(!matches.has(key))matches.set(key,{value,label:value+(owner?' · '+owner:'')});
    }
    return Array.from(matches.values());
  }
  function el(tag, text) { const node=document.createElement(tag); if(text!==undefined)node.textContent=String(text); return node; }
  function mount({host, fields, customers, addresses, customerInput, addressInput, statusBox}) {
    if(!host || !customerInput || !addressInput) return;
    host.querySelector('[data-moses-identity-review]')?.remove();
    const holder=el('div');holder.dataset.mosesIdentityReview='true';
    holder.style.cssText='display:grid;gap:10px;background:#f8fafc;border:1px solid #cdd8e3;padding:12px;border-radius:12px;margin:12px 0';
    holder.append(el('strong','Verify customer and service location'));
    holder.append(el('small','Choose saved records below. Extracted text is a suggestion, not a verified identity. Nothing is saved until you press the dispatch Save button.'));
    const rawCustomer=str(fields?.customer), rawAddress=str(fields?.address);
    const c=companyCandidates(rawCustomer,customers);
    const customerBlock=el('div');customerBlock.append(el('div','PDF customer: '+(rawCustomer||'Not identified')));
    const customerSelect=el('select');customerSelect.className='input';
    const customerOptions = [{value:'',label:'Select a saved customer…'},...c];
    for(const option of customerOptions){const node=el('option',option.label);node.value=option.value;customerSelect.append(node);}
    if(c.length===1)customerSelect.value=c[0].value;
    customerBlock.append(customerSelect);
    if(!c.length)customerBlock.append(el('small','No verified saved customer match. Use + New Customer or select an existing customer manually.'));
    else if(c.length>1)customerBlock.append(el('small','Multiple customer names match. Choose the intended saved company.'));
    holder.append(customerBlock);
    const addrBlock=el('div');addrBlock.append(el('div','PDF service address: '+(rawAddress||'Not identified')));
    const addressSelect=el('select');addressSelect.className='input';
    function updateAddresses(){
      addressSelect.replaceChildren();const base=el('option','Select a saved service address…');base.value='';addressSelect.append(base);
      // Customer-profile addresses are also saved identity records.
      const profileAddresses=(customers||[]).filter(x => (!customerSelect.value || words(x.company_name||x.name)===words(customerSelect.value)))
        .map(x=>({address:x.address||x.site_address||x.job_address,customer:x.company_name||x.name}));
      const found=addressCandidates(rawAddress,[...(addresses||[]),...profileAddresses],customerSelect.value);
      for(const a of found){const node=el('option',a.label);node.value=a.value;addressSelect.append(node);}
      if(found.length===1)addressSelect.value=found[0].value;
      info.textContent=found.length?'Choose the saved job-site address and confirm.':'No matching saved address. Use + New Address or enter a manually verified site address.';
    }
    const info=el('small');addrBlock.append(addressSelect,info);holder.append(addrBlock);
    customerSelect.addEventListener('change',updateAddresses);updateAddresses();
    const buttons=el('div');buttons.style.cssText='display:flex;flex-wrap:wrap;gap:8px';
    const apply=el('button','Apply verified selections');apply.type='button';apply.className='btn btn-orange';
    apply.addEventListener('click',()=>{
      let applied=0;
      const selectedCustomer=customerSelect.value, selectedAddress=addressSelect.value;
      if(selectedCustomer){
        if(customerInput.value.trim() && words(customerInput.value)!==words(selectedCustomer) && !root.confirm('Replace the customer currently entered in the dispatch form?'))return;
        customerInput.value=selectedCustomer;customerInput.dispatchEvent(new Event('input',{bubbles:true}));customerInput.dispatchEvent(new Event('change',{bubbles:true}));applied++;
      }
      if(selectedAddress){
        if(addressInput.value.trim() && normStreet(addressInput.value)!==normStreet(selectedAddress) && !root.confirm('Replace the service address currently entered in the dispatch form?'))return;
        addressInput.value=selectedAddress;addressInput.dispatchEvent(new Event('input',{bubbles:true}));addressInput.dispatchEvent(new Event('change',{bubbles:true}));applied++;
      }
      statusBox.textContent += ' '+(applied?applied+' verified saved identity field(s) applied.':'Choose a saved customer/address above, or use the existing New buttons.');
    });
    buttons.append(apply);
    if(rawAddress){
      const manual=el('button','Use PDF address after manual verification');manual.type='button';manual.className='btn';
      manual.addEventListener('click',()=>{
        if(!root.confirm('Confirm the PDF Ship To address is the actual service location. This will not create a saved address.'))return;
        if(addressInput.value.trim() && !root.confirm('Replace the existing service address?'))return;
        addressInput.value=rawAddress;addressInput.dispatchEvent(new Event('input',{bubbles:true}));
        statusBox.textContent += ' Manually verified address entered; save it using + New Address if needed.';
      });buttons.append(manual);
    }
    holder.append(buttons);host.append(holder);
    return {customerCount:c.length};
  }
  root.MosesIdentityReview={mount,companyCandidates,addressCandidates,words,addressParts};
  if(typeof module==='object' && module.exports)module.exports=root.MosesIdentityReview;
})(typeof window!=='undefined'?window:globalThis);
