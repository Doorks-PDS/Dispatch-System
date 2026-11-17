"""Moses delivery desk: verified linkage only, no external sends or real PDF writes."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers import moses_drafts as m


class Jobs:
    def __init__(self):
        self.jobs = [{'id': 'job-abc', 'job_number': '1126-05',
                      'customer': 'Example Property', 'status': 'Quote',
                      'completion_forms': [{'id': 'form-abc', 'ready_to_quote': True,
                                            'recommendations': 'Replace damaged closer'}]}]
    def get_job(self, identity):
        return next((j for j in self.jobs if j['id'] == identity), None)
    def list_jobs(self):
        return self.jobs


class Docs:
    def __init__(self):
        self.docs = []
    def list_documents(self):
        return self.docs


@pytest.fixture
def env(tmp_path):
    jobs, docs = Jobs(), Docs()
    req = SimpleNamespace(
        state=SimpleNamespace(auth_user={'id': 'office'}, auth_role='office_admin'),
        session={'active_platform': 'pds'},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path,
                                                  calendar_store=jobs, documents_store=docs)))
    item = m.prepare_batch(req)['items'][0]
    saved = m.update_draft(item['id'], m.DraftEdit(version=1, scope='Replace closer',
                            parts_review='none_specified', freight_review='not_required'), req)['item']
    approved = m.decide_draft(item['id'],m.DraftDecision(version=saved['version'], approve=True), req)['item']
    return req, jobs, docs, approved


def doc(number='RE00123', job_id='job-abc', job_number='1126-05', customer='Example Property',kind='estimate'):
    return {'type':kind, 'number':number, 'filename':number+'.pdf',
            'job_id':job_id, 'job_number':job_number, 'customer':customer}


def test_empty_saved_documents(env):
    req,_,_,ticket=env
    assert m.delivery_documents(ticket['id'],req)['items']==[]
    assert m.delivery_documents(ticket['id'],req)['read_only'] is True


def test_exact_document_linkage_is_read_only(env):
    req,jobs,docs,ticket=env
    docs.docs=[doc(),doc('RE00124'), doc('RE00125',job_id='other'), doc('JS00044',kind='invoice'),
               doc('RE00126', customer='Another Company'),doc('RE00127',job_number='wrong')]
    result=m.delivery_documents(ticket['id'],req)
    assert result['count']==2
    assert [i['number'] for i in result['items']]==['RE00124','RE00123']
    assert result['sent'] is False
    assert not hasattr(docs,'send')


def test_legacy_document_number_only_with_unique_job_number(env):
    req,jobs,docs,ticket=env
    docs.docs=[doc(job_id='')]
    assert m.delivery_documents(ticket['id'],req)['count']==1
    jobs.jobs.append({'id':'another','job_number':'1126-05','customer':'Example Property'})
    assert m.delivery_documents(ticket['id'],req)['count']==0


def test_bare_customer_match_never_allowed(env):
    req,_,docs,ticket=env
    docs.docs=[doc(job_id='',job_number='')]
    assert m.delivery_documents(ticket['id'],req)['count']==0


def test_job_customer_or_number_changed_block(env):
    req,jobs,docs,ticket=env
    docs.docs=[doc()]
    jobs.jobs[0]['customer']='New owner'
    with pytest.raises(HTTPException) as e:m.delivery_documents(ticket['id'],req)
    assert e.value.status_code==409
    jobs.jobs[0]['customer']='Example Property'
    jobs.jobs[0]['job_number']='1126-99'
    with pytest.raises(HTTPException) as e:m.delivery_documents(ticket['id'],req)
    assert e.value.status_code==409


def test_cross_workspace_and_technician_forbidden(env):
    req,_,docs,ticket=env;docs.docs=[doc()]
    req.session['active_platform']='doorks'
    with pytest.raises(HTTPException) as e:m.delivery_documents(ticket['id'],req)
    assert e.value.status_code==403
    req.session['active_platform']='pds';req.state.auth_role='technician'
    with pytest.raises(HTTPException) as e:m.delivery_documents(ticket['id'],req)
    assert e.value.status_code==403


def test_reopened_or_declined_ticket_cannot_prepare_delivery(env):
    req,_,docs,ticket=env;docs.docs=[doc()]
    m.reopen_draft(ticket['id'],m.DraftReopen(version=ticket['version']),req)
    with pytest.raises(HTTPException) as e:m.delivery_documents(ticket['id'],req)
    assert e.value.status_code==409


def test_invalid_and_missing_draft_fails_closed(env):
    req,_,_,_=env
    for identifier in ['not-an-id','f'*32]:
        with pytest.raises(HTTPException) as e:m.delivery_documents(identifier,req)
        assert e.value.status_code in (404,422)


def test_existing_sent_quote_does_not_hide_delivery_history(env):
    req,jobs,docs,ticket=env
    docs.docs=[doc()]
    jobs.jobs[0]['sent_quote_number']='RE00123'
    assert m.delivery_documents(ticket['id'],req)['count']==1


def test_storage_corruption_blocks_delivery(env):
    req,_,_,ticket=env
    path=m._file(req);path.write_text('invalid json')
    with pytest.raises(HTTPException) as e:m.delivery_documents(ticket['id'],req)
    assert e.value.status_code==503
    assert path.read_text()=='invalid json'


def test_delivery_route_registered():
    paths=[route.path for route in m.router.routes]
    assert '/moses-drafts/{draft_id}/delivery' in paths


def test_no_direct_email_or_pdf_send_in_delivery_endpoint():
    import inspect
    source=inspect.getsource(m.delivery_documents)+inspect.getsource(m._linked_estimate_documents)
    assert 'send_resend_attachment' not in source
    assert 'create_estimate' not in source
