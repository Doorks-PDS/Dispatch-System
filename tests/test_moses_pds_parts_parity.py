from types import SimpleNamespace
from pathlib import Path
from io import BytesIO
import pytest
from fastapi import HTTPException, UploadFile
from app.routers import data, moses


def req(tmp_path, platform='pds', role='office_admin'):
    state=SimpleNamespace(project_root=tmp_path, data_dir=tmp_path, auth_user={'id':'admin'}, auth_role=role)
    return SimpleNamespace(app=SimpleNamespace(state=state),state=state,session={'active_platform':platform})


def test_pds_part_url_supplier_and_image_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(data, '_parts_path', lambda request: tmp_path/'parts_catalog.json')
    request=req(tmp_path)
    created=data.create_part(request,data.PartPayload(manufacturer='LCN',part_number='4040XP',description='Closer',supplier='Vendor A',price=125,product_url='https://supplier.example/item',image_url='https://supplier.example/photo.jpg'),None)['item']
    saved=data.list_parts(request,None)['items'][0]
    assert saved['id']==created['id']
    assert saved['product_url']=='https://supplier.example/item'
    assert saved['image_url']=='https://supplier.example/photo.jpg'
    assert saved['supplier']=='Vendor A'
    assert saved['Item']=='4040XP' and saved['Price']==125
    updated=data.update_part(request,created['id'],data.PartPayload(manufacturer='LCN',part_number='4040XP',description='Closer',supplier='Vendor B',price=130,product_url='https://supplier.example/new',image_url=''),None)['item']
    assert updated['supplier']=='Vendor B'
    assert updated['product_url']=='https://supplier.example/new'
    assert data.list_parts(request,None)['items'][0]['Price']==130


def test_pds_part_rejects_unsafe_external_links(tmp_path,monkeypatch):
    monkeypatch.setattr(data, '_parts_path', lambda request:tmp_path/'parts_catalog.json')
    for link in ['http://supplier.example/item','javascript:alert(1)','https://user:password@website.test/part']:
        with pytest.raises(HTTPException) as ex:
            data.create_part(req(tmp_path),data.PartPayload(part_number='A',product_url=link),None)
        assert ex.value.status_code==400


def test_pds_part_photo_restricted_to_pds_workspace(tmp_path):
    directory=tmp_path/'business_workspaces'/'pds'/'part_images'
    directory.mkdir(parents=True)
    name='a'*32+'.png'
    (directory/name).write_bytes(b'\x89PNG\r\n\x1a\ncontent')
    response=moses.get_pds_part_image(name,req(tmp_path))
    assert Path(response.path)==directory/name
    with pytest.raises(HTTPException) as ex:
        moses.get_pds_part_image(name,req(tmp_path,'sdc'))
    assert ex.value.status_code==403
    with pytest.raises(HTTPException) as ex:
        moses.get_pds_part_image('../bad.png',req(tmp_path))
    assert ex.value.status_code==404


@pytest.mark.asyncio
async def test_pds_photo_upload_and_reject_other_platform(tmp_path):
    file=UploadFile(filename='part.png',file=BytesIO(b'\x89PNG\r\n\x1a\nphoto'))
    result=await moses.upload_pds_part_image(req(tmp_path),file)
    assert result['url'].startswith('/moses/part-image/pds/')
    name=result['url'].split('/')[-1]
    assert (tmp_path/'business_workspaces'/'pds'/'part_images'/name).exists()
    with pytest.raises(HTTPException) as ex:
        await moses.upload_pds_part_image(req(tmp_path,'doorks'),UploadFile(filename='x.png',file=BytesIO(b'\x89PNG\r\n\x1a\nphoto')))
    assert ex.value.status_code==403
