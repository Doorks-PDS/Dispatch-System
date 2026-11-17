from pathlib import Path

APP = Path(__file__).resolve().parents[1] / 'static' / 'app.js'
SOURCE = APP.read_text()


def test_pds_directory_reuses_existing_records_and_vendor_directory():
    assert 'async function renderGroupedCustomersTab()' in SOURCE
    assert 'apiListCustomers().catch(() => [])' in SOURCE
    assert 'apiListContacts().catch(() => [])' in SOURCE
    assert "label:'Customers & Contacts',description:'Customer profiles with their contacts.'" in SOURCE
    assert "label:'Vendors',description:'Subcontractors and service partners.'" in SOURCE
    assert "renderPdsServiceVendors" in SOURCE


def test_new_dispatch_saved_site_is_explicit_but_address_remains_free_text():
    assert "locationSelect.setAttribute('aria-label','Saved customer locations')" in SOURCE
    assert 'Select a saved location or enter a new address below' in SOURCE
    assert "row1.append(locationRow);updateLocations();" in SOURCE
    assert "if(!locationSelect.value)return;addressInput.value=locationSelect.value" in SOURCE
    assert "addressInput.addEventListener('input',()=>{if(locationSelect.value!==addressInput.value)locationSelect.value='';});" in SOURCE


def test_customer_bound_suggestions_without_blocking_new_sites():
    assert 'customerSpecificAddressStrings([], (knownAddresses || []), company)' in SOURCE
    assert 'combinedAddressStrings((extraAddresses || []), (knownAddresses || []))' in SOURCE
    assert 'input.addEventListener("change", apply)' in SOURCE
    assert 'input.addEventListener("blur", apply)' not in SOURCE
