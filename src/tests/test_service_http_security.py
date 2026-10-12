from contextlib import contextmanager
from http.client import HTTPConnection
import json
from threading import Thread

import pytest

from atot import service_http

TOKEN = 'synthetic-http-test-token-' + 'x' * 32


@contextmanager
def server(monkeypatch):
    calls = []
    monkeypatch.setattr(service_http, 'handle_service_request', lambda request: calls.append(request) or {'ok': True})
    instance = service_http.create_http_server('127.0.0.1', 0, token=TOKEN)
    thread = Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance, calls
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize('host', ['0.0.0.0', '192.0.2.1', 'example.com'])
def test_http_rejects_nonlocal_bind(host):
    with pytest.raises(ValueError, match='loopback'):
        service_http.create_http_server(host, 0, token=TOKEN)


def test_http_requires_a_strong_token():
    with pytest.raises(ValueError, match='ATOT_HTTP_TOKEN'):
        service_http.create_http_server('127.0.0.1', 0, token='')


@pytest.mark.parametrize('headers,status', [
    ({}, 401), ({'Authorization': 'Bearer wrong'}, 401),
    ({'Origin': 'https://example.com'}, 403), ({'Origin': 'null'}, 403),
    ({'Host': 'evil.example'}, 403), ({'Content-Type': 'text/plain'}, 400),
    ({'Transfer-Encoding': 'chunked'}, 400),
])
def test_http_rejects_untrusted_requests_without_dispatch(monkeypatch, headers, status):
    with server(monkeypatch) as (instance, calls):
        defaults = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
        if not headers:
            defaults.pop('Authorization')
        connection = HTTPConnection('127.0.0.1', instance.server_port, timeout=3)
        connection.request('POST', '/request', body='{}', headers={**defaults, **headers})
        response = connection.getresponse()
        assert response.status == status
        response.read()
        connection.close()
        assert calls == []


def test_http_accepts_authenticated_local_json_and_never_caches(monkeypatch):
    with server(monkeypatch) as (instance, calls):
        request = {'id': 'test', 'method': 'status', 'params': {}}
        connection = HTTPConnection('127.0.0.1', instance.server_port, timeout=3)
        connection.request('POST', '/request', body=json.dumps(request), headers={
            'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json; charset=utf-8'})
        response = connection.getresponse()
        assert response.status == 200
        assert response.getheader('Cache-Control') == 'no-store'
        assert json.loads(response.read())['ok'] is True
        assert calls == [request]
        connection.close()
