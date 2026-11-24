"""5.66: do not mistake provider acceptance for recipient delivery."""
import json
from pathlib import Path
from types import SimpleNamespace
from app.services import moses_po_delivery as po
from app.services import moses_pds_document_email as doc

ROOT=Path(__file__).resolve().parents[1]


def _request(tmp_path):
    return SimpleNamespace(
        state=SimpleNamespace(auth_user={'id':'a1','name':'Office Admin'},auth_role='office_admin'),
        session={'active_platform':'pds'},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))),
    )


def test_po_history_reads_signed_webhook_observations_without_sending(tmp_path, monkeypatch):
    monkeypatch.delenv('MOSES_PO_SEND_ENABLED',raising=False)
    request=_request(tmp_path)
    path=tmp_path/'moses_pds'/'moses_po_delivery_actions.json';path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{
        'id':'approval1','record_id':'po1','platform':'pds',
        'snapshot':{'to':'vendor@example.test','subject':'Purchase Order PO-00003',
            'reply_to':'office@example.test','cc':'','number':'PO-00003',
            'total':'100.00','lines':[('Part','1','100.00')]},
        'state':'sent','transport':'resend','provider_message_id':'resend_id_abc',
        'delivery_status':'accepted_by_provider','requested_at':'2026-11-24T20:00:00+00:00',
        'completed_at':'2026-11-24T20:01:00+00:00'
    }]))
    before=po.history(request,'pds','po1')
    assert before[0]['delivery_status']=='accepted_by_provider'
    assert before[0]['to']=='vendor@example.test'
    assert before[0]['completed_at']=='2026-11-24T20:01:00+00:00'
    event_path=tmp_path/'moses_resend_delivery_events.json'
    event_path.write_text(json.dumps([{'event_id':'evt1','provider_message_id':'resend_id_abc',
        'delivery_status':'delivered_to_recipient_server','occurred_at':'2026-11-24T20:02:00+00:00'}]))
    observed=po.history(request,'pds','po1')
    assert observed[0]['delivery_status']=='delivered_to_recipient_server'
    assert observed[0]['delivery_event_at']=='2026-11-24T20:02:00+00:00'
    assert json.loads(path.read_text())[0]['state']=='sent'


def test_document_history_exposes_sender_and_time_without_claiming_delivery():
    row={'id':'approval1','state':'sent','snapshot':{'kind':'estimate','number':'RE00097',
      'job_number':'100344','to':'customer@example.test','from':'NoReply@example.test',
      'reply_to':'estimates@example.test','subject':'Estimate RE00097','filename':'RE00097.pdf',
      'cc':''},'provider_message_id':'email_abc','requested_at':'2026-11-24T20:00:00+00:00',
      'completed_at':'2026-11-24T20:01:00+00:00','delivery_status':'accepted_by_provider'}
    result=doc._public(row)
    assert result['requested_at'] and result['completed_at']
    assert result['delivery_status']=='accepted_by_provider'
    assert result['attachment_filename']=='RE00097.pdf'


def test_job_ticket_and_purchase_order_show_compact_history():
    js=(ROOT/'static/app.js').read_text()
    assert 'function pdsEmailHistoryDisclosure(endpoint)' in js
    assert 'function pdsEmailDeliveryLabel(item)' in js
    assert 'Delivered to recipient mail server (inbox not verified)' in js
    assert "row.append(pdsEmailHistoryDisclosure('/moses-pds-email/'" in js
    assert "poEmailHistoryHost.append(pdsEmailHistoryDisclosure(" in js
    assert "if(item.id)poEmailHistoryHost.append" in js
