/* Doorks shared work-order presentation: office and external portals.
   Data and permissions remain enforced by their existing authenticated APIs. */
(function(root){
 'use strict';
 function node(tag,cls,value){const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined&&value!==null)e.textContent=String(value);return e}
 function nonempty(v){return v!==undefined&&v!==null&&String(v).trim()!==''}
 // Rev95: one ticket field schema and DOM renderer for office and portal views.
 // Office-only metadata is not exposed in customer/vendor tickets.
 const ticketFieldSchema=Object.freeze([
   {label:'Job #',keys:['job_number','work_order_number','number'],office:true},
   {label:'Address',keys:['address']},
   {label:'Contact',keys:['contact','contact_name']},
   {label:'Phone',keys:['phone','contact_phone']},
   {label:'Email',keys:['email'],office:true},
   {label:'PO #',keys:['po_number'],office:true},
   {label:'Estimate #',keys:['estimate_number'],office:true},
   {label:'Sent Estimate #',keys:['sent_quote_number'],office:true},
   {label:'Quote Assigned To',keys:['quote_assigned_to'],office:true},
   {label:'Invoice #',keys:['invoice_number'],office:true},
   {label:'Service type',keys:['service_type']},
   {label:'Priority',keys:['priority','urgency']},
   {label:'Description',keys:['description','scope']},
   {label:'Scheduled date',keys:['scheduled_date']},
   {label:'Scheduled time',keys:['scheduled_time']},
   {label:'Job location',keys:['job_location']},
   {label:'Access instructions',keys:['access_instructions','site_access_instructions']}
 ]);
 function renderTicketFields(host,record,options={}){
   if(!host)throw Error('Ticket fields host required');
   const r=record||{},role=String(options.role||'office').toLowerCase();
   const office=role==='office'||role==='admin';
   host.replaceChildren();host.classList.add(office?'grid2':'dst-grid');
   for(const field of ticketFieldSchema){
     if(field.office&&!office)continue;
     if(options.only&& !options.only.includes(field.label))continue;
     const value=field.keys.map(k=>r[k]).find(nonempty);
     if(!office&&!nonempty(value))continue;
     const cell=node('div',office?'':'dst-cell');
     if(office){cell.append(node('div','label',field.label),node('div','field',value??''));}
     else cell.append(node('small','',field.label),node('div','',value));
     host.append(cell);
   }
   if(!host.childElementCount&&!office)host.append(node('p','dst-muted','No details available.'));
   return host;
 }
 function render(host,record,options={}){
   if(!host)throw Error('Ticket host required');
   const r=record||{},role=options.role||'office';
   host.replaceChildren();host.classList.add('doorks-shared-ticket');
   const head=node('header','dst-header');
   const title=node('div','dst-title');title.append(node('small','dst-eyebrow','DOORKS  /  WORK ORDER'),node('h2','',r.job_number||r.work_order_number||r.number||'Work order'));
   const state=node('span','dst-status',r.status||'Pending');head.append(title,state);host.append(head);
   const groups=[['Service information',['Address','Contact','Phone','Service type','Priority','Description']],['Dispatch & scheduling',['Scheduled date','Scheduled time','Job location','Access instructions']]];
   for(const [name,labels] of groups){const section=node('section','dst-section');section.append(node('h3','',name));const grid=node('div');renderTicketFields(grid,r,{role,only:labels});section.append(grid);host.append(section)}
   if(role==='vendor'&&Array.isArray(r.vendor_assignments)&&r.vendor_assignments.length){const section=node('section','dst-section');section.append(node('h3','','Vendor progress'));for(const a of r.vendor_assignments){const row=node('div','dst-activity');row.append(node('strong','',a.status||'Assigned'),node('p','',[a.scope,a.vendor_field_notes,a.vendor_parts_needed,a.vendor_estimated_arrival].filter(nonempty).join(' · ')));section.append(row)}host.append(section)}
   if(options.note){host.append(node('p','dst-permissions',options.note))}
   return host;
 }
 function renderDocument(host,documentRecord,options={}){
   const d=documentRecord||{};host.replaceChildren();host.classList.add('doorks-shared-ticket');
   const head=node('header','dst-header');const heading=node('div','dst-title');heading.append(node('small','dst-eyebrow',options.vendor?'VENDOR SUBMISSION  /  OFFICE REVIEW':'DOORKS  /  DOCUMENT'),node('h2','',(d.document_type||'Estimate').toUpperCase()+' · '+(d.reference||d.document_number||'Draft')));head.append(heading,node('span','dst-status',d.status||'Draft'));host.append(head);
   const section=node('section','dst-section');const grid=node('div','dst-grid');for(const [label,value] of [['Work order',d.work_order_number],['Customer',d.customer],['Service address',d.address],['Prepared by',d.vendor_name||d.company]]){if(nonempty(value)){const cell=node('div','dst-cell');cell.append(node('small','',label),node('div','',value));grid.append(cell)}}section.append(grid);host.append(section);
   const lines=Array.isArray(d.line_items)?d.line_items:[];
   const table=node('table','dst-table');const thead=node('thead');const header=node('tr');
   for(const name of ['Description','Qty','Rate','Amount'])header.append(node('th','',name));
   thead.append(header);table.append(thead);const body=node('tbody');
   for(const line of lines){const qty=lineQuantity(line),rate=lineRate(line);
     const tr=node('tr');for(const value of [line.description||line.item||line.name||'',qty,'$'+rate.toFixed(2),'$'+(qty*rate).toFixed(2)])tr.append(node('td','',value));body.append(tr)}
   table.append(body);host.append(table);
   const totals=calculateDocumentTotals(lines,Number(d.tax_rate||0));
   // Issued office amounts are authoritative: a portal summary may omit taxes or lines.
   const issued=Number(d.amount);const hasIssued=d.amount!==undefined&&d.amount!==null&&d.amount!==''&&Number.isFinite(issued);
   host.append(node('p','dst-total','Total: $'+(hasIssued?issued:totals.total).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})));
   if(!lines.length)host.append(node('p','dst-permissions','No itemized lines were released. Request the original document from the office before approval.'));
   if(options.vendor)host.append(node('p','dst-permissions','Vendor proposal only. Office approval and issuance are required before customer delivery.'));
   return host;
 }
 // Canonical document model shared by the office builder and portal editor.
 // Preserve the original objects so office-specific metadata and permissions survive.
 function lineQuantity(line){return Number(line.qty??line.quantity??0)||0}
 function lineRate(line){return Number(line.rate??line.unit_price??0)||0}
 function calculateDocumentTotals(lines,taxPercent=0){
   const items=Array.isArray(lines)?lines:[];
   const categories={trip:0,fuel:0,labor:0,parts:0,other:0};
   let subtotal=0,taxableSubtotal=0;
   for(const line of items){
     const amount=lineQuantity(line)*lineRate(line);
     subtotal+=amount;
     if(line.taxable!==false)taxableSubtotal+=amount;
     const kind=String(line.kind||'other').toLowerCase();
     const category=kind==='part'||kind==='parts'?'parts':(['trip','fuel','labor'].includes(kind)?kind:'other');
     categories[category]+=amount;
   }
   const tax=taxableSubtotal*(Number(taxPercent)||0)/100;
   return {subtotal,taxableSubtotal,tax,total:subtotal+tax,categories};
 }
 // Rev101: common validation for the actual office builder and vendor proposal editor.
 // Office may retain intentional zero-quantity draft rows; issuing documents cannot.
 function validateDocumentLines(lines,options={}){
   const errors=[];
   if(!Array.isArray(lines)||!lines.length)return {valid:false,errors:['Add at least one line item.']};
   lines.forEach((line,index)=>{
     const qty=Number(line.qty??line.quantity);
     const rate=Number(line.rate??line.unit_price);
     const label='Line '+(index+1)+': ';
     if(!String(line.description||'').trim())errors.push(label+'description required');
     if(!Number.isFinite(qty)||qty<=0)errors.push(label+'quantity must be greater than zero');
     if(!Number.isFinite(rate)||rate<0)errors.push(label+'rate cannot be negative');
     if(Number.isFinite(qty)&&Number.isFinite(rate)&&qty*rate>100000000)errors.push(label+'amount exceeds the permitted limit');
   });
   return {valid:!errors.length,errors};
 }
 // Rev105: canonical vendor submission built from the same line model as preview.
 // Never creates an office invoice or assigns an office document number.
 function buildVendorDocumentSubmission(context={}){
   const type=String(context.documentType||'').toLowerCase();
   if(!['estimate','invoice'].includes(type))throw Error('Invalid vendor document type');
   const assignment=String(context.assignmentId||'').trim();
   if(!assignment)throw Error('Vendor assignment is required');
   const lines=Array.isArray(context.items)?context.items:[];
   const validation=validateDocumentLines(lines);
   if(!validation.valid)throw Error(validation.errors.join('; '));
   const normalized=lines.map(line=>({
     description:String(line.description||'').trim(),
     quantity:Number(line.qty??line.quantity),
     rate:Number(line.rate??line.unit_price)
   }));
   const total=calculateDocumentTotals(normalized).subtotal;
   if(!Number.isFinite(total)||total<0||total>100000000)throw Error('Vendor document total is out of range');
   const reference=String(context.reference||'').trim();
   if(reference.length>100)throw Error('Reference must be 100 characters or fewer');
   return {
     assignment_id:assignment,document_type:type,
     description:normalized.map(line=>line.quantity+' × '+line.description+' @ $'+line.rate.toFixed(2)).join('\n'),
     amount:Number(total.toFixed(2)),line_items:normalized,
     reference,note:'Itemized vendor proposal'
   };
 }
 // Rev94: shared, configurable line-item row. Both office and vendor use this
 // DOM implementation; office-only part lookup and tax controls remain callbacks.
 function createDocumentLineRow(item,index,options={}){
   const office=options.mode==='office',quantityKey=office?'qty':(options.quantityKey==='qty'?'qty':'quantity');
   const row=node(office?'tr':'div',office?'':'portal-line-row');
   const wrap=(control)=>{if(office){const td=node('td');td.style.cssText='padding:8px;border-bottom:1px solid #f3f4f6';td.append(control);row.append(td)}else row.append(control)};
   const makeInput=(key)=>{
     const input=node('input',office?'input':'');input.dataset.k=key;
     input.type=key==='description'||key==='code'?'text':'number';input.value=item[key]??'';
     if(input.type==='number'){input.min=key===quantityKey?(office?'0':'0.01'):'0';input.step=key===quantityKey&&office?'0.25':'0.01'}
     if(!office){input.required=true;input.placeholder=key;input.style.cssText='width:100%;min-width:0;padding:9px;border:1px solid #cbd5dc;border-radius:8px'}
     if(office&&key===quantityKey)input.style.minWidth='72px';if(office&&key==='rate')input.style.minWidth='96px';
     input.addEventListener(key==='code'?'change':'input',()=>{
       item[key]=input.type==='number'&&office?Number(input.value||0):input.value;
       if(typeof options.onFieldChange==='function')options.onFieldChange(item,key,input.value,index);
       if(typeof options.onChange==='function')options.onChange(item,key,index);
     });wrap(input);return input;
   };
   if(office)makeInput('code');makeInput('description');makeInput(quantityKey);makeInput('rate');
   if(office){const tax=node('input');tax.type='checkbox';tax.dataset.k='taxable';tax.checked=item.taxable!==false;tax.addEventListener('change',()=>{item.taxable=tax.checked;options.onChange?.(item,'taxable',index)});const label=node('label');label.style.cssText='display:flex;align-items:center;gap:6px';label.append(tax,node('span','hint','Tax'));wrap(label);const amount=node('span');amount.dataset.k='line_total';amount.textContent='$'+(lineQuantity(item)*lineRate(item)).toFixed(2);wrap(amount)}
   const remove=node('button',office?'btn':'',office?'×':'×');remove.type='button';remove.dataset.k='del';remove.setAttribute('aria-label','Remove line item');remove.addEventListener('click',()=>options.onRemove?.(index));wrap(remove);
   return row;
 }
 // Shared editable line-item controller. The same instance supplies preview and submission
 // values; it does not grant permission to issue customer-facing documents.
 function createLineEditor(host,options={}){
   if(!host)throw Error('Line editor host required');
   // A portal editor must never become an implicit office document issuer.
   const role=String(options.role||'vendor').toLowerCase();
   if(role!=='vendor')throw Error('Line editor is limited to vendor proposals');
   const items=Array.isArray(options.items)?options.items:[];
   const onChange=typeof options.onChange==='function'?options.onChange:()=>{};
   const rows=node('div','dst-line-editor');host.replaceChildren(rows);
   const total=node('strong','dst-total');
   const add=node('button','dst-add-line','+ Add line item');add.type='button';
   const amount=()=>calculateDocumentTotals(items).subtotal;
   const validate=()=>validateDocumentLines(items);
   const update=()=>{total.textContent='Total: $'+amount().toFixed(2);onChange(items,amount())};
   function redraw(){
     rows.replaceChildren();
     items.forEach((item,index)=>rows.append(createDocumentLineRow(item,index,{quantityKey:options.quantityKey,onChange:update,onRemove:(i)=>{items.splice(i,1);redraw()}})));update();
   }
   add.addEventListener('click',()=>{items.push({description:'',[options.quantityKey==='qty'?'qty':'quantity']:1,rate:0});redraw()});
   host.append(add,total);if(!items.length)items.push({description:'',[options.quantityKey==='qty'?'qty':'quantity']:1,rate:0});redraw();
   return {items,redraw,amount,validate};
 }
 // Shared document workspace: the office retains its authoritative issuance drawer,
 // while vendor proposals use the same row editor, totals, draft reference and preview.
 // This controller deliberately never creates an office invoice number or issues a PDF.
 function createDocumentWorkspace(host,options={}){
   if(!host)throw Error('Document workspace host required');
   const role=String(options.role||'').toLowerCase();
   if(role==='office'||role==='admin'){
     if(!nativeOffice.document)throw Error('Office document controller is not registered');
     return nativeOffice.document(options);
   }
   if(role!=='vendor')throw Error('Document editing is not permitted for this role');
   const type=String(options.documentType||'estimate').toLowerCase();
   if(!['estimate','invoice'].includes(type))throw Error('Invalid document type');
   const items=Array.isArray(options.items)?options.items:[];
   const wrapper=node('section','dst-document-workspace');
   const heading=node('h3','',type==='invoice'?'Vendor invoice draft':'Vendor estimate draft');
   const notice=node('p','dst-notice','For office review only. No customer-facing document is issued.');
   const referenceLabel=node('label','', 'Vendor document reference (optional)');
   const reference=node('input');reference.type='text';reference.maxLength=100;reference.placeholder='Your document reference';reference.value=String(options.reference||'');referenceLabel.append(reference);
   reference.addEventListener('input',()=>{preview.hidden=true;options.onChange?.(items)});
   const lineHost=node('div','dst-workspace-lines');
   const previewButton=node('button','dst-add-line','Preview document');previewButton.type='button';
   const preview=node('div','dst-document-preview');preview.hidden=true;
   wrapper.append(heading,notice,referenceLabel,lineHost,previewButton,preview);
   host.replaceChildren(wrapper);
   const editor=createLineEditor(lineHost,{role:'vendor',items,onChange:()=>{preview.hidden=true;options.onChange?.(items)},quantityKey:options.quantityKey});
   const draft=()=>({document_type:type,reference:reference.value.trim(),work_order_number:options.workOrderNumber||'',customer:options.customer||'',address:options.address||'',line_items:items});
   previewButton.addEventListener('click',()=>{const check=editor.validate();if(!check.valid){preview.replaceChildren(node('p','',check.errors.join('; ')));preview.hidden=false;return}renderDocument(preview,draft(),{vendor:true});preview.hidden=false});
   return {items,redraw:editor.redraw,amount:editor.amount,validate:editor.validate,reference,draft,preview};
 }
 // Both roles validate their document data before persistence; only the office
 // API can allocate RE/JS numbers, save customer documents or issue PDFs.
 function validateDocumentDraft(context={}){
   const role=String(context.role||'').toLowerCase();
   if(!['office','admin','vendor'].includes(role))throw Error('Document editing is not permitted for this role');
   const errors=validateDocumentLines(context.items).errors.slice();
   if(role==='office'||role==='admin'){
     if(!String(context.customer||'').trim())errors.push('Customer is required');
     if(!String(context.number||'').trim())errors.push('Document number is required');
     if(!String(context.preparedBy||'').trim())errors.push('Prepared by is required');
     const tax=Number(context.taxRate);
     if(!Number.isFinite(tax)||tax<0||tax>100)errors.push('Sales tax rate must be between 0 and 100');
   }
   return {valid:!errors.length,errors};
 }
 // Rev97: one DOM input factory for office ticket editing and portal change requests.
 // This builds controls only; persistence remains in the authenticated role-specific handlers.
 function createTicketFieldInput(field,options={}){
   const role=String(options.role||'office').toLowerCase();
   if(!['office','admin','customer','vendor'].includes(role))throw Error('Unsupported ticket editor role');
   const kind=String(field||'').toLowerCase();
   const allowed=['address','contact','phone','email','po_number','estimate_number','invoice_number','quote_assigned_to','sent_quote_number','requested_date','requested_time'];
   if(!allowed.includes(kind))throw Error('Unsupported ticket field');
   if(!['office','admin'].includes(role)&&!['requested_date','requested_time'].includes(kind))throw Error('Portal cannot edit office ticket fields');
   const input=node('input',options.className||'input');
   input.type=kind==='requested_date'?'date':kind==='requested_time'?'time':kind==='email'?'email':kind==='phone'?'tel':'text';
   if(options.id)input.id=String(options.id);
   if(options.list)input.setAttribute('list',String(options.list));
   input.value=options.value==null?'':String(options.value);
   input.setAttribute('aria-label',options.label||kind.replace(/_/g,' '));
   if(options.required)input.required=true;
   return input;
 }
 // Rev99: one role-aware ticket edit panel using the same input controls as
 // the office ticket and portal request form. Never authorizes persistence.
 const editableTicketFields=Object.freeze({
   address:'Address',contact:'Contact',phone:'Phone',email:'Email',
   po_number:'Purchase order',estimate_number:'Estimate number',
   invoice_number:'Invoice number',quote_assigned_to:'Quote assigned to',
   sent_quote_number:'Sent estimate number',requested_date:'Requested date',
   requested_time:'Requested time'
 });
 function createTicketEditPanel(host,options={}){
   if(!host)throw Error('Ticket editor host required');
   const role=String(options.role||'').toLowerCase();
   if(!capabilities(role).viewTicket)throw Error('Ticket editor role not permitted');
   const fields=Array.isArray(options.fields)?options.fields:[];
   if(!fields.length)throw Error('Ticket editor requires explicit fields');
   if(typeof options.submit!=='function')throw Error('Authenticated save or request handler required');
   const form=node('form','dst-ticket-edit');
   const inputs=Object.create(null);
   for(const field of fields){
     if(!Object.prototype.hasOwnProperty.call(editableTicketFields,field))throw Error('Unknown ticket edit field');
     // createTicketFieldInput rejects office-controlled fields for portal roles.
     const label=node('label','dst-edit-label',editableTicketFields[field]);
     const input=createTicketFieldInput(field,{role,value:(options.values||{})[field],label:editableTicketFields[field]});
     label.append(input);form.append(label);inputs[field]=input;
   }
   const save=node('button','dst-save',capabilities(role).office?'Save changes':'Submit request');
   save.type='submit';const feedback=node('p','dst-request-feedback');feedback.setAttribute('role','status');
   form.append(save,feedback);
   form.addEventListener('submit',async event=>{
     event.preventDefault();if(save.disabled)return;
     const values=Object.create(null);
     for(const field of fields)values[field]=inputs[field].value;
     save.disabled=true;
     try{
       const result=await options.submit(values);
       feedback.textContent=(result&&result.message)||(capabilities(role).office?'Changes saved.':'Request submitted for office review.');
     }catch(error){feedback.textContent=error&&error.message||'Unable to submit changes.'}
     finally{save.disabled=false}
   });
   host.append(form);return {form,inputs,feedback};
 }
 // Rev96: one role-configured ticket change-request editor. This is a request,
 // never a direct mutation of office-owned dispatch fields.
 function createTicketChangeRequest(host,options={}){
   if(!host)throw Error('Change request host required');
   const role=String(options.role||'').toLowerCase();
   if(!['customer','vendor'].includes(role))throw Error('Only customer and vendor requests are supported');
   if(typeof options.submit!=='function')throw Error('Authenticated request submission is required');
   const vendor=role==='vendor';
   const choices=vendor?[['schedule','Schedule'],['scope','Scope of work'],['access','Site access'],['contact','Site contact'],['other','Other']]:[['details_update','Update job details'],['schedule_change','Request schedule change'],['cancel_request','Request cancellation'],['question','Ask the office']];
   const form=node('form','dst-change-request');
   const type=node('select');type.setAttribute('aria-label','Change request type');
   for(const [value,label] of choices){const opt=node('option','',label);opt.value=value;type.append(opt)}
   const date=createTicketFieldInput('requested_date',{role,label:'Requested date',className:''});
   const time=createTicketFieldInput('requested_time',{role,label:'Requested time',className:''});
   const note=node('textarea');note.required=true;note.minLength=3;note.maxLength=3000;note.setAttribute('aria-label','Change request explanation');note.placeholder='Describe the requested change and why it is needed';
   const submit=node('button','submit','Submit change request');submit.type='submit';
   const feedback=node('p','dst-request-feedback');feedback.setAttribute('role','status');
   form.append(type,date,time,note,submit,feedback);
   form.addEventListener('submit',async event=>{
     event.preventDefault();if(submit.disabled)return;
     if(!note.value.trim()||note.value.trim().length<(vendor?5:3)){feedback.textContent='Please explain the request (at least '+(vendor?5:3)+' characters).';return}
     submit.disabled=true;
     try{
       const payload=vendor?{change_type:type.value,proposed_date:date.value,proposed_time:time.value,explanation:note.value.trim()}:{request_type:type.value,requested_date:date.value,requested_time:time.value,note:note.value.trim()};
       const result=await options.submit(payload);
       feedback.textContent=(result&&result.message)||'Request submitted for office review. Confirmed dispatch details have not changed.';
       note.value='';
     }catch(error){feedback.textContent=error.message||'Unable to submit request.'}
     finally{submit.disabled=false}
   });
   host.append(form);return {form,type,date,time,note,feedback};
 }
 // Rev93: a single office-controller registry with explicit role boundaries.
 // Existing office implementations are delegated unchanged until their DOM can be
 // safely extracted. Portal writes must still be authorized by the server.
 const nativeOffice=Object.create(null);
 function registerOfficeControllers(controllers){
   for(const key of ['ticket','document']){
     if(controllers && typeof controllers[key]==='function')nativeOffice[key]=controllers[key];
   }
   return {ticket:!!nativeOffice.ticket,document:!!nativeOffice.document};
 }
 function capabilities(role){
   const name=String(role||'').toLowerCase();
   return Object.freeze({
     office:name==='office'||name==='admin',
     viewTicket:['office','admin','vendor','customer'].includes(name),
     editDispatch:name==='office'||name==='admin',
     issueDocument:name==='office'||name==='admin',
     proposeDocument:name==='vendor',
     respondToEstimate:name==='customer'
   });
 }
 function openTicket(context={}){
   const policy=capabilities(context.role);
   if(!policy.viewTicket)throw Error('Ticket access is not available for this role');
   if(policy.office){
     if(!nativeOffice.ticket)throw Error('Office ticket controller is not registered');
     return nativeOffice.ticket(context);
   }
   if(!context.host)throw Error('Portal ticket host required');
   return render(context.host,context.record||{}, {role:context.role,note:context.note});
 }
 function openDocument(context={}){
   const policy=capabilities(context.role);
   if(policy.office){
     if(!nativeOffice.document)throw Error('Office document controller is not registered');
     return nativeOffice.document(context);
   }
   if(policy.proposeDocument){
     if(!context.host)throw Error('Vendor document editor host required');
     return createDocumentWorkspace(context.host,{...context,role:context.role});
   }
   throw Error('Document editing is not permitted for this role');
 }
 function officeControllerStatus(){return Object.freeze({ticket:!!nativeOffice.ticket,document:!!nativeOffice.document})}
 root.DoorksSharedTicket={render,renderTicketFields,ticketFieldSchema,renderDocument,createLineEditor,createDocumentWorkspace,validateDocumentDraft,createDocumentLineRow,calculateDocumentTotals,validateDocumentLines,buildVendorDocumentSubmission,createTicketChangeRequest,createTicketFieldInput,createTicketEditPanel,registerOfficeControllers,capabilities,openTicket,openDocument,officeControllerStatus};
})(window);
