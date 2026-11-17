"""Offline tests: actual new Moses review service; no customer docs or sending."""
from types import SimpleNamespace
import json
import pytest
from fastapi import HTTPException
from app.routers import moses_drafts as m


class Calendar:
    def __init__(self):
        self.jobs = [{'id': 'job-123', 'job_number': '1126-01', 'customer': 'A Customer',
                      'status': 'Quote', 'completion_forms': [{
                        'id': 'form-123', 'ready_to_quote': True,
                        'recommendations': 'Replace storefront closer',
                        'parts_required': 'Closer assembly', 'time_required': '2 hours'}]}]
        self.writes = 0
    def get_job(self, ident):
        return next((x for x in self.jobs if x['id'] == ident), None)
    def list_jobs(self):
        return self.jobs


@pytest.fixture
def state(tmp_path, monkeypatch):
    from app.routers import data
    catalog = tmp_path/'parts_catalog.json'
    catalog.write_text(json.dumps({'items':[{'part_number':'CL-100','description':'Storefront Closer', 'price':185},
                                           {'part_number':'CL-200','description':'Closer bracket','price':60}]}))
    monkeypatch.setattr(data, '_parts_path', lambda req: catalog)
    store=Calendar()
    request=SimpleNamespace(state=SimpleNamespace(auth_user={'id':'office'}, auth_role='office_admin'),
       session={'active_platform':'pds'},app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path,calendar_store=store)))
    return request, store, catalog


def draft(state):
    request,_,_=state
    return m.prepare_batch(request)['items'][0]


def approve(state, parts_review='hold', freight_review='hold', selected_parts=None):
    request,_,_=state
    item=draft(state)
    changed=m.update_draft(item['id'],m.DraftEdit(version=item['version'],scope='Install closer per field recommendation',
      parts_review=parts_review,freight_review=freight_review,selected_parts=selected_parts or []),request)['item']
    return m.decide_draft(item['id'],m.DraftDecision(version=changed['version'],approve=True),request)['item']


def test_handoff_rejects_unapproved(state):
    request,_,_=state;item=draft(state)
    with pytest.raises(HTTPException) as e:m.estimator_handoff(item['id'],request)
    assert e.value.status_code==409


def test_reviewed_scope_and_hold_are_safe(state):
    request,store,_=state
    ticket=approve(state)
    h=m.estimator_handoff(ticket['id'],request)
    assert h['verified'] is True and h['scope']=='Install closer per field recommendation'
    assert h['freight_review']=='hold' and not h['official_estimate_created'] and not h['email_sent']
    assert store.writes==0


def test_catalog_quantity_reference_not_price(state):
    request,_,_=state
    ticket=approve(state, parts_review='matched',freight_review='required', selected_parts=[{'part_number':'CL-100','quantity':2}])
    h=m.estimator_handoff(ticket['id'],request)
    assert h['selected_parts']==[{'part_number':'CL-100','quantity':2,'description':'Storefront Closer'}]
    assert 'price' not in str(h).lower() or h.get('requires_pricing_review') is True
    assert h['requires_pricing_review'] is True


def test_unknown_catalog_part_blocks_match(state):
    request,_,_=state;item=draft(state)
    with pytest.raises(HTTPException) as e:m.update_draft(item['id'],m.DraftEdit(version=1,scope='Quote',
      parts_review='matched',freight_review='required',selected_parts=[{'part_number':'NOPE','quantity':1}]),request)
    assert e.value.status_code==409


def test_duplicate_bad_quantity_and_unselected_match_block(state):
    request,_,_=state;item=draft(state)
    for selected in [[{'part_number':'CL-100','quantity':0}],
                     [{'part_number':'CL-100','quantity':1},{'part_number':'cl-100','quantity':1}],[]]:
        with pytest.raises(HTTPException):m.update_draft(item['id'],m.DraftEdit(version=1,scope='Quote',parts_review='matched',
            freight_review='not_required',selected_parts=selected),request)


def test_form_edits_after_review_block_handoff(state):
    request,store,_=state;ticket=approve(state)
    store.jobs[0]['completion_forms'][0]['recommendations']='Different scope, newly added'
    with pytest.raises(HTTPException) as e:m.estimator_handoff(ticket['id'],request)
    assert e.value.status_code==409


def test_sent_quote_or_removed_job_blocks_handoff(state):
    request,store,_=state;ticket=approve(state)
    store.jobs[0]['sent_quote_number']='RE00092'
    with pytest.raises(HTTPException):m.estimator_handoff(ticket['id'],request)
    store.jobs.clear()
    with pytest.raises(HTTPException):m.estimator_handoff(ticket['id'],request)


def test_catalog_changes_after_approval_block_handoff(state):
    request,_,catalog=state
    ticket=approve(state,parts_review='matched',freight_review='not_required',selected_parts=[{'part_number':'CL-100','quantity':1}])
    catalog.write_text(json.dumps({'items':[]}))
    with pytest.raises(HTTPException):m.estimator_handoff(ticket['id'],request)


def test_cross_workspace_and_technician_denied(state):
    request,_,_=state;ticket=approve(state)
    request.session['active_platform']='doorks'
    with pytest.raises(HTTPException) as e:m.estimator_handoff(ticket['id'],request)
    assert e.value.status_code==403
    request.session['active_platform']='pds';request.state.auth_role='tech'
    with pytest.raises(HTTPException) as e:m.estimator_handoff(ticket['id'],request)
    assert e.value.status_code==403


def test_old_form_without_fingerprint_fails_closed(state):
    request,_,_=state
    ticket=approve(state)
    path=m._file(request)
    rows=json.loads(path.read_text());rows[0].pop('source_form_digest');path.write_text(json.dumps(rows))
    with pytest.raises(HTTPException) as e:m.estimator_handoff(ticket['id'],request)
    assert e.value.status_code==409


def test_reopen_hold_to_review_and_reapprove(state):
    request,_,_=state
    item=approve(state,freight_review='hold')
    fresh=m.reopen_draft(item['id'],m.DraftReopen(version=item['version']),request)['item']
    assert fresh['state']=='pending_review' and fresh['version']==item['version']+1
    edited=m.update_draft(item['id'],m.DraftEdit(version=fresh['version'],scope='Verified scope',
        parts_review='hold',freight_review='not_required'),request)['item']
    approved=m.decide_draft(item['id'],m.DraftDecision(version=edited['version'],approve=True),request)['item']
    assert m.estimator_handoff(item['id'],request)['freight_review']=='not_required'
    assert approved['state']=='ready_for_estimator'
    assert m._read(m._file(request))[0]['review_events'][0]['action']=='reopened'


def test_reopen_denies_cross_workspace_and_stale_versions(state):
    request,_,_=state;item=approve(state)
    with pytest.raises(HTTPException):m.reopen_draft(item['id'],m.DraftReopen(version=1),request)
    request.state.auth_role='technician'
    with pytest.raises(HTTPException):m.reopen_draft(item['id'],m.DraftReopen(version=item['version']),request)
