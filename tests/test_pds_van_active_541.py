"""Van setup must not offer historical inactive staff."""
from types import SimpleNamespace
from app.routers.pds_van_stock import _people


class Employees:
    def list(self):
        return [
            {'id':'active','name':'Current Technician','role':'tech'},
            {'id':'former','name':'Former Technician','role':'tech'},
            {'id':'retired','name':'Retired Technician','role':'tech','status':'Inactive'},
        ]


class Users:
    def list_users(self):
        return [
            {'id':'account1','name':'Current Technician','role':'tech','active':True},
            {'id':'account2','name':'Former Technician','role':'tech','active':False},
            {'id':'account3','name':'Account Only Tech','role':'tech','active':False},
        ]


def test_inactive_accounts_excluded_from_eligible_van_setup():
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(employees_store=Employees(),users_store=Users())))
    staff = _people(req)
    assert 'active' in staff
    assert 'former' not in staff
    assert 'retired' not in staff
    assert 'account3' not in staff
