#!/usr/bin/env python3
"""Apply Phase 2R-J-D to CURRENT app/routers/workspaces.py. Does not touch saved data."""
from pathlib import Path
import ast, re, sys
p=Path('app/routers/workspaces.py')
if not p.is_file():sys.exit('STOP: workspaces router missing')
s=p.read_text()
if 'RJD_DOCUMENT_SEQUENCE_V1' in s:sys.exit('Already patched; no changes.')
try:
    tree=ast.parse(s)
    assign=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='KINDS' for t in n.targets))
    kinds=ast.literal_eval(assign.value)
except Exception as exc:sys.exit(f'STOP: unexpected KINDS definition: {exc}')
if not isinstance(kinds,dict) or not {'doorks','sdc'}.issubset(kinds):sys.exit('STOP: workspace configuration changed')
# Patch only the sdc tuple in the literal, if needed.
if 'estimates_invoices' not in kinds['sdc']:
    literal=ast.get_source_segment(s,assign.value)
    m=re.search(r'''(['"]sdc['"]\s*:\s*\()([^)]*)(\))''',literal)
    if not m or not re.search(r'''['"]purchase_orders['"]''',m.group(2)):sys.exit('STOP: SDC tuple structure changed')
    body=m.group(2).rstrip()
    if not body.endswith(','):body+=','
    body+='"estimates_invoices",'
    newliteral=literal[:m.start(2)]+body+literal[m.end(2):]
    s=s.replace(literal,newliteral,1)
create_marker='        item={"id":uuid.uuid4().hex,"created_at":datetime.now(timezone.utc).isoformat(),**data}'
if s.count(create_marker)!=1:sys.exit('STOP: create function changed; no files written')
create_injection='''        # RJD_DOCUMENT_SEQUENCE_V1: server-owned, per-workspace, per-type numbering.
        if kind=="estimates_invoices":
            doc_type=str(data.get("document_type") or "").strip().title()
            if doc_type not in ("Estimate","Invoice"):
                raise HTTPException(400,"Document type must be Estimate or Invoice")
            prefix="EST" if doc_type=="Estimate" else "INV"
            counter_path=path.parent/("estimate_sequence.json" if doc_type=="Estimate" else "invoice_sequence.json")
            current=0
            if counter_path.exists():
                current=int(json.loads(counter_path.read_text(encoding="utf-8")).get("last",0))
            for old in items:
                if str(old.get("document_type","")).lower()!=doc_type.lower():continue
                match=re.fullmatch(prefix+r"-(\\d+)",str(old.get("document_number", "")))
                if match:current=max(current,int(match.group(1)))
            data.pop("document_number",None)
            data["document_type"]=doc_type
            data["document_number"]=f"{prefix}-{current+1:05d}"
            if "status" not in data:data["status"]="Draft"
            # Reserve before writing document; skipped numbers are safer than reused numbers.
            temp=counter_path.with_suffix(".tmp")
            with temp.open("w",encoding="utf-8") as f:
                json.dump({"last":current+1},f);f.flush();os.fsync(f.fileno())
            os.replace(temp,counter_path)
'''
s=s.replace(create_marker,create_injection+create_marker,1)
update_marker='                item.update(data);'
if s.count(update_marker)!=1:sys.exit('STOP: update function changed; no files written')
s=s.replace(update_marker,'''                if kind=="estimates_invoices":
                    data.pop("document_number",None)
                    data.pop("document_type",None)
'''+update_marker,1)
try:compile(s,str(p),'exec')
except Exception as exc:sys.exit(f'STOP: generated syntax error: {exc}')
p.write_text(s)
print('Patched current workspaces.py: SDC collection, separate EST/INV counters, immutable numbers and document types.')
