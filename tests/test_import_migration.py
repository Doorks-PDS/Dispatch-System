from app.routers import ai_data_import as imp

def test_historical_identifiers_are_preserved_as_identity():
    assert imp._dedupe_key({'job_number':'0120-4'},'work_orders') == '0120-4'
    assert imp._dedupe_key({'work_order_number':'0120-4'},'work_orders') == '0120-4'
    assert imp._dedupe_key({'document_number':'RE00001','document_type':'Estimate'},'estimates_invoices') == ('estimate','re00001')

def test_duplicate_preflight_does_not_consider_different_contacts_duplicate():
    existing=[{'name':'ViaSat','contact':'Larry'}]
    stage={'rows':[{'name':'ViaSat','contact':'Mike'}, {'name':'ViaSat','contact':'Larry'}]}
    result=imp._preview_status(stage,existing,'customers')
    assert result['eligible']==1
    assert result['duplicate_count']==1

def test_numbered_records_detect_existing_and_in_batch_duplicates():
    existing=[{'job_number':'0120-4'}]
    stage={'rows':[{'job_number':'0120-4'}, {'job_number':'0120-5'}, {'job_number':'0120-5'}]}
    result=imp._preview_status(stage,existing,'work_orders')
    assert result['eligible']==1
    assert result['duplicate_count']==2
