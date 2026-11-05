from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]

def test_new_endpoints():
    tree=ast.parse((ROOT/'app/routers/doorks_operations.py').read_text())
    names={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    assert {'pto_ledger','add_pto_entry','post_pto_accrual','payment_reconciliation','allocate_payment','relationship_hubs'} <= names

def test_duplicate_guards():
    s=(ROOT/'app/routers/doorks_operations.py').read_text()
    assert 'Accrual already posted for this period' in s
    assert 'Payment already allocated; duplicate prevented' in s
    assert 'Payment reference does not match invoice number' in s

def test_frontend_links():
    s=(ROOT/'static/app.js').read_text()
    for n in ('renderDoorksPaymentReconciliation','renderDoorksPTO','renderDoorksRelationshipHub'):
        assert 'function '+n in s
