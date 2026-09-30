import socket
import pytest
from app.crawler.transport import public_addresses
from app.crawler.robots import RobotsPolicy
from app.crawler.url_discovery import normalize_url,same_site
import httpx


@pytest.mark.asyncio
async def test_private_dns_rejected(monkeypatch):
    import asyncio
    async def private(*args,**kw): return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]
    monkeypatch.setattr(asyncio.get_running_loop(),'getaddrinfo',private)
    with pytest.raises(ValueError): await public_addresses('https://public-looking.example/')


def test_normalization_and_exact_boundary():
    assert normalize_url('https://EXAMPLE.com/a?utm_source=x&b=2&a=1#top')=='https://example.com/a?a=1&b=2'
    assert not same_site('https://evil.example.com','https://example.com')
    with pytest.raises(ValueError): normalize_url('https://user:secret@example.com')


@pytest.mark.asyncio
async def test_robots_failure_closed_and_404_open():
    class Transport:
        delay=1
        status=503
        async def get(self,url,**kwargs): return httpx.Response(self.status,text='',request=httpx.Request('GET',url))
    t=Transport()
    assert not await RobotsPolicy(t).can_fetch('https://example.com/')
    t.status=404
    assert await RobotsPolicy(t).can_fetch('https://example.com/')


@pytest.mark.asyncio
async def test_redirect_private_address_never_requested(monkeypatch):
    import app.crawler.transport as module
    calls=[]
    async def resolve(url):
        if '127.0.0.1' in url: raise ValueError('private')
        return ['93.184.216.34']
    monkeypatch.setattr(module,'public_addresses',resolve)
    def handler(request):
        calls.append(request)
        return httpx.Response(302,headers={'location':'http://127.0.0.1/secret'})
    original=httpx.AsyncClient
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError): await module.SafeTransport().get('https://example.com/')
    assert len(calls)==1
    assert calls[0].headers['host']=='example.com'


@pytest.mark.asyncio
async def test_compressed_response_decoded_exactly_once(monkeypatch):
    import gzip
    import app.crawler.transport as module
    async def resolve(url): return ['93.184.216.34']
    monkeypatch.setattr(module,'public_addresses',resolve)
    original=httpx.AsyncClient
    def handler(request): return httpx.Response(200,headers={'content-encoding':'gzip'},content=gzip.compress(b'hello world'))
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler)))
    response=await module.SafeTransport().get('https://example.com/')
    assert response.text=='hello world'
