"""Ensure the existing source-backed PDS multi-scope inspection is exposed to Moses."""
from pathlib import Path
import ast

SRC = Path(__file__).resolve().parents[1] / 'app/services/moses_agent.py'


def test_scope_tool_is_registered_only_in_pds_agent():
    tree = ast.parse(SRC.read_text())
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    scope = [n for n in funcs if n.name == 'get_pds_separate_estimate_scopes']
    assert len(scope) == 1
    assert len(scope[0].args.args) == 1
    assert scope[0].args.args[0].arg == 'job_id'
    registration = SRC.read_text().split('tools=(', 1)[1].split('    # Apply limits', 1)[0]
    assert registration.count('get_pds_separate_estimate_scopes') == 1
    pds = registration.split("if platform == 'pds'", 1)[0].rsplit('[', 1)[-1]
    assert 'get_pds_separate_estimate_scopes' in pds


def test_scope_agent_is_read_only_and_reuses_existing_service():
    tree = ast.parse(SRC.read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'get_pds_separate_estimate_scopes')
    code = ast.unparse(fn)
    assert "platform != 'pds'" in code
    assert 'moses_pds_estimate_scopes import inspect' in code
    assert 'inspect(request, job_id)' in code
    assert 'create_estimate' not in code
    assert 'send_email' not in code


def test_pds_agent_instructions_guide_source_linked_scope_review():
    source = SRC.read_text()
    assert 'call get_pds_separate_estimate_scopes using the exact job ID' in source
    assert 'flag ambiguous splits for office review' in source
