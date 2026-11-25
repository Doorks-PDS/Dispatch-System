from app.services.pds_qbo_sync_readiness import identify_party

ROWS = [{'pds_id': 'c-1', 'name': 'Example Customer', 'active': True}]
LINKS = {'customers:c-1': {'kind': 'customers', 'pds_id': 'c-1',
    'source_name': 'Example Customer', 'provider_name': 'Example Customer',
    'provider_id': '123', 'company_id': '100', 'environment': 'sandbox'}}


def resolve(rows=ROWS, links=LINKS, name='Example Customer', company='100'):
    return identify_party(name, rows, links, kind='customers', company=company,
                          environment='sandbox')


def test_approved_identity_is_read_only_hint():
    assert resolve()['status'] == 'approved_master_link'
    assert resolve()['provider_id'] == '123'


def test_name_comparison_is_space_and_case_insensitive():
    assert resolve(name='  EXAMPLE    CUSTOMER ')['status'] == 'approved_master_link'


def test_company_change_invalidates_link():
    assert resolve(company='101')['provider_id'] is None


def test_duplicate_source_names_never_guess():
    result = resolve(rows=ROWS + [{'pds_id': 'c-2', 'name': 'Example Customer', 'active': True}])
    assert result['status'] == 'ambiguous_source'


def test_missing_source_is_not_approved():
    assert resolve(name='Unknown')['status'] == 'source_not_found'


def test_unapproved_source_is_not_silently_linked():
    assert resolve(links={})['status'] == 'approval_required'


def test_stale_local_name_rejected():
    changed = [dict(ROWS[0], name='Renamed customer')]
    assert resolve(rows=changed, name='Renamed customer')['status'] == 'stale_or_wrong_company'


def test_bad_provider_id_rejected():
    links = {'customers:c-1': dict(LINKS['customers:c-1'], provider_id='bad-id')}
    assert resolve(links=links)['provider_id'] is None
