from app.routers.doorks_packages import manifest

def test_payroll_in_all_packages():
    packages=manifest()['packages']
    assert all(p['payroll_included'] and 'payroll' in p['features'] for p in packages.values())

def test_public_intake_routes_registered():
    from app.routers.doorks_portals import router
    paths={r.path for r in router.routes}
    assert '/doorks-portals/public/service-request' in paths
    assert '/doorks-portals/request-service' in paths
