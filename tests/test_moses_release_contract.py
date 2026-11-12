"""Moses release guardrails. These run without network, browser or production data."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_moses_routes_have_explicit_guard_before_storage_access():
    tree = ast.parse((ROOT / 'app/routers/moses_command.py').read_text())
    functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    endpoints = [node for node in functions.values() if any(
        isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == 'router'
        for decorator in node.decorator_list)]
    assert len(endpoints) >= 10
    for endpoint in endpoints:
        assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == '_guard' for n in ast.walk(endpoint)), endpoint.name


def test_moses_router_never_introduces_external_execution_clients():
    source = (ROOT / 'app/routers/moses_command.py').read_text()
    tree = ast.parse(source)
    forbidden = ('subprocess', 'smtplib', 'requests', 'httpx', 'stripe', 'boto3', 'selenium')
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    names = [alias.name for node in imports for alias in (node.names if isinstance(node, ast.Import) else [])]
    names += [node.module or '' for node in imports if isinstance(node, ast.ImportFrom)]
    assert not any(name.split('.')[0] in forbidden for name in names)
    assert 'external_execution_enabled": False' in source


def test_moses_ui_requires_manual_review_and_has_voice_stop():
    app = (ROOT / 'static/app.js').read_text()
    assert 'Review and press Send to Moses.' in app
    assert 'stopSpeaking();stopListening()' in app
    assert 'expected_draft_version' in app
    assert 'file-deliverable' in app


def test_router_registered_once():
    source = (ROOT / 'main.py').read_text()
    assert source.count('app.include_router(moses_command_router)') == 1
