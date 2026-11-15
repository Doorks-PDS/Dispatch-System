"""Rev93: legacy editor and Moses must cooperate on one filesystem lock."""
import inspect
import json
import multiprocessing as mp
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services.doorks_supplier_bill_lock import supplier_bill_lock
from app.services import moses_supplier_bill_actions as moses
from app.routers import doorks_workflow as workflow


def request(path):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=str(path))),
         state=SimpleNamespace(auth_user={'id':'admin'},auth_role='office_admin'),
         session={'active_platform':'doorks'})


def holder(path, started, release):
    with supplier_bill_lock(request(path)):
        started.set()
        release.wait(10)


def contender(path, started, done):
    started.wait(10)
    with supplier_bill_lock(request(path)):
        done.set()


def test_cross_process_lock_blocks_second_worker(tmp_path):
    ctx=mp.get_context('fork')
    started=ctx.Event();release=ctx.Event();done=ctx.Event()
    first=ctx.Process(target=holder,args=(tmp_path,started,release))
    second=ctx.Process(target=contender,args=(tmp_path,started,done))
    first.start()
    try:
        assert started.wait(5)
        second.start()
        assert not done.wait(.3), 'second worker entered while first held the lock'
        release.set()
        assert done.wait(5)
    finally:
        release.set()
        first.join(5)
        if second.pid:second.join(5)
        if first.is_alive():first.terminate();first.join()
        if second.pid and second.is_alive():second.terminate();second.join()
    assert first.exitcode==0 and second.exitcode==0


def test_legacy_bill_writes_and_moses_use_same_lock():
    assert 'with supplier_bill_lock(request)' in inspect.getsource(workflow.bill)
    assert 'with supplier_bill_lock(request)' in inspect.getsource(workflow.supplier_payment)
    assert 'with supplier_bill_lock(request)' in inspect.getsource(moses.locked)


def test_lock_released_on_exception(tmp_path):
    with pytest.raises(ValueError):
        with supplier_bill_lock(request(tmp_path)):
            raise ValueError('abort')
    with supplier_bill_lock(request(tmp_path)):
        pass
