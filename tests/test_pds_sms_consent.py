from app.services.pds_sms_consent import handle_keyword, can_send, current_state


def test_keyword_double_opt_in_and_duplicate(tmp_path):
    kw = lambda sid, message: handle_keyword(tmp_path, '+17605550123', sid, message,
                             privacy_url='https://example.org/pds/sms/privacy',
                             terms_url='https://example.org/pds/sms/terms')
    assert not can_send(tmp_path, '+17605550123')
    assert kw('sid-yes-before', 'YES')[1] == 'unknown'
    assert kw('sid-start', 'START')[1] == 'pending'
    assert not can_send(tmp_path, '+17605550123')
    result = kw('sid-confirm', 'YES')
    assert result[1] == 'subscribed'
    assert can_send(tmp_path, '+17605550123')
    assert kw('sid-confirm', 'YES') == result
    assert kw('sid-stop', 'STOP')[1] == 'unsubscribed'
    assert not can_send(tmp_path, '+17605550123')
    assert kw('sid-help', 'HELP')[1] == 'unsubscribed'
    assert kw('sid-start2', 'START')[1] == 'pending'
    assert kw('sid-confirm2', 'YES')[1] == 'subscribed'
