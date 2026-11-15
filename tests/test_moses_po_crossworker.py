"""Rev94: existing PO writers and Moses receipts participate in same file lock."""
import inspect
import multiprocessing as mp
from types import SimpleNamespace
import pytest
from app.services.doorks_po_lock import po_write_lock
from app.services import moses_receiving_actions
from app.routers import pds_purchase_orders, workspaces, doorks_workflow


def request(path):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=str(path))))


def _holder(path, platform, entered, release):
    with po_write_lock(request(path), platform):
        entered.set()
        release.wait(10)


def _contender(path, platform, entered, acquired):
    entered.wait(10)
    with po_write_lock(request(path), platform):
        acquired.set()


def test_cross_process_same_workspace_blocks(tmp_path):
    ctx = mp.get_context('fork')
    entered, release, acquired = ctx.Event(), ctx.Event(), ctx.Event()
    first = ctx.Process(target=_holder, args=(tmp_path, 'doorks', entered, release))
    second = ctx.Process(target=_contender, args=(tmp_path, 'doorks', entered, acquired))
    first.start()
    try:
        assert entered.wait(5)
        second.start()
        assert not acquired.wait(.25)
        release.set()
        assert acquired.wait(5)
    finally:
        release.set()
        first.join(5)
        if second.pid: second.join(5)
        if first.is_alive(): first.terminate(); first.join()
        if second.pid and second.is_alive(): second.terminate(); second.join()
    assert first.exitcode == 0 and second.exitcode == 0


def test_nested_lock_and_error_release(tmp_path):
    for platform in ('pds', 'doorks', 'sdc'):
        with pytest.raises(ValueError):
            with po_write_lock(request(tmp_path), platform):
                with po_write_lock(request(tmp_path), platform):
                    raise ValueError('interrupted operation')
        with po_write_lock(request(tmp_path), platform):
            pass


def test_invalid_and_mixed_workspace(tmp_path):
    with pytest.raises(ValueError):
        with po_write_lock(request(tmp_path), '../pds'):
            pass
    with po_write_lock(request(tmp_path), 'pds'):
        with pytest.raises(RuntimeError):
            with po_write_lock(request(tmp_path), 'sdc'):
                pass


def test_existing_write_routes_share_lock():
    for fn in (pds_purchase_orders.create_order, pds_purchase_orders.update_order,
               pds_purchase_orders.receive_po, workspaces.create, workspaces.update,
               workspaces.delete, doorks_workflow.receive,
               moses_receiving_actions.propose, moses_receiving_actions.decide):
        assert 'po_write_lock(' in inspect.getsource(fn), fn.__name__
