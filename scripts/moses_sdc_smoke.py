"""Opt-in, read-only SDC Agents SDK smoke test. No HTTP server required.

Usage: python scripts/moses_sdc_smoke.py --check
       python scripts/moses_sdc_smoke.py --live --data-dir /path/to/render/data
The --live option calls OpenAI and may incur API charges. It never writes business records.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import os
import json
from pathlib import Path
from types import SimpleNamespace

FILES = ('orders.json', 'expenses.json', 'software_leads.json',
         'estimates_invoices.json', 'receivables.json')

def snapshots(data_dir: Path):
    root = data_dir / 'business_workspaces' / 'sdc'
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in FILES if (root / name).is_file()}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='Check SDK and key without contacting OpenAI')
    mode.add_argument('--live', action='store_true', help='Make one real, read-only SDC agent call')
    parser.add_argument('--data-dir', type=Path, help='Doorks persistent data directory (required for --live)')
    args = parser.parse_args()
    sdk = importlib.util.find_spec('agents') is not None
    key = bool(os.getenv('OPENAI_API_KEY'))
    print('Agents SDK:', 'available' if sdk else 'NOT INSTALLED')
    print('OPENAI_API_KEY:', 'configured' if key else 'NOT CONFIGURED')
    if args.check:
        return 0 if sdk and key else 2
    if not sdk or not key:
        print('Live test stopped: SDK and API key are required.')
        return 2
    if not args.data_dir or not args.data_dir.is_dir():
        print('Live test stopped: supply a valid --data-dir. No test call was made.')
        return 2
    before = snapshots(args.data_dir)
    if not before:
        print('Live test stopped: no SDC source files found at the expected data path.')
        return 2
    request = SimpleNamespace(
        state=SimpleNamespace(auth_user='moses-smoke-test', auth_role='office_admin'),
        session={'active_platform': 'sdc'},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=args.data_dir)))
    from app.services.moses_agent import answer
    from app.routers import doorks_assistant
    # Instrument the authorized dispatcher: a plausible model sentence alone
    # is not proof the agent actually retrieved the saved records.
    original = doorks_assistant._execute_sdc_tool
    calls = []
    def audited_dispatch(req, name, arguments=None):
        result = original(req, name, arguments)
        calls.append((name, result))
        return result
    doorks_assistant._execute_sdc_tool = audited_dispatch
    try:
        response = answer(request, 'How many saved SDC orders and expenses do we have? Use the record-count tool.', [])
        print('Agent answer:', response[:1200])
        verified = [result for name, result in calls if name == 'get_business_record_counts'
                    and isinstance(result, dict)
                    and isinstance(result.get('orders'), dict)
                    and isinstance(result.get('expenses'), dict)
                    and 'error' not in result['orders'] and 'error' not in result['expenses']]
        if not verified:
            print('FAIL: Agent did not successfully invoke the authorized record-count tool.')
            return 1
        print('Verified tool result:', json.dumps(verified[-1], sort_keys=True)[:1200])
        return 0 if response.strip() and 'could not complete' not in response.lower() else 1
    except Exception as exc:
        print('Live agent test failed:', type(exc).__name__, str(exc)[:300])
        return 1
    finally:
        doorks_assistant._execute_sdc_tool = original
        after = snapshots(args.data_dir)
        if after != before:
            print('WARNING: SDC data-file hashes changed during smoke test. Investigate before deploying.')
            raise RuntimeError('SDC source data changed during read-only smoke test')
        print('Read-only integrity: verified for', len(before), 'SDC files')

if __name__ == '__main__':
    raise SystemExit(main())
