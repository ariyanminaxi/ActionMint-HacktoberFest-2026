from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.meetings.sample import SAMPLE_TRANSCRIPT

client=TestClient(app)
HEADERS={'X-App-Token':settings.app_token}

def test_health_is_public_and_does_not_expose_secrets():
    r=client.get('/health')
    assert r.status_code==200
    assert r.json()['status']=='ok'
    assert 'gemini_api_key' not in r.text.lower()

def test_meeting_roundtrip_and_edit():
    created=client.post('/api/meetings',headers=HEADERS,json={'source':'transcript','title':'Launch sync','meeting_date':'2026-10-26','text':SAMPLE_TRANSCRIPT})
    assert created.status_code==201
    meeting_id=created.json()['meeting_id']; token=created.json()['session_token']
    auth={**HEADERS,'X-Session-Token':token}
    client.post(f'/api/meetings/{meeting_id}/finalize',headers=auth)
    stream=client.get(f'/api/meetings/{meeting_id}/events',headers=auth)
    assert stream.status_code==200
    assert 'event: spec' in stream.text and 'event: done' in stream.text
    result=client.get(f'/api/meetings/{meeting_id}/result',headers=auth)
    assert result.status_code==200
    spec=result.json()['spec']
    assert spec['action_items'][0]['due_iso']=='2026-10-30'
    spec['title']='Edited launch sync'
    updated=client.put(f'/api/meetings/{meeting_id}/result',headers=auth,json=spec)
    assert updated.status_code==200
    assert 'Edited launch sync' in updated.json()['md']

def test_missing_app_token_is_rejected():
    r=client.post('/api/meetings',json={'source':'transcript','text':'hello'})
    assert r.status_code==401


def test_health_reports_unconfigured_providers_without_pretending(monkeypatch):
    import dataclasses
    from app import config, main as main_module
    from app.providers import base
    patched=dataclasses.replace(config.settings,provider_chain=('gemini','groq','mock'),gemini_api_key='',groq_api_key='')
    monkeypatch.setattr(main_module,'settings',patched)
    monkeypatch.setattr(base,'settings',patched)
    body=client.get('/health').json()
    providers={p['name']:p for p in body['providers']}
    assert [p['name'] for p in body['providers']]==['gemini','groq','mock']
    assert providers['gemini']=={'name':'gemini','ok':False,'latency_ms':None,'configured':False}
    assert providers['groq']=={'name':'groq','ok':False,'latency_ms':None,'configured':False}
    assert providers['mock']['ok'] is True
    assert body['default_provider']=='mock'


def _new_meeting() -> tuple[str, dict]:
    created = client.post('/api/meetings', headers=HEADERS, json={'source': 'link', 'title': 'Bot check'})
    assert created.status_code == 201
    body = created.json()
    return body['meeting_id'], {**HEADERS, 'X-Session-Token': body['session_token']}


def test_bot_rejects_non_meet_platform_with_the_contract_error():
    meeting_id, auth = _new_meeting()
    for url in ('https://zoom.us/j/123', 'https://teams.microsoft.com/l/meetup-join/x',
                'https://meet.google.com.evil.com/abc-defg-hij'):
        response = client.post(f'/api/meetings/{meeting_id}/bot', headers=auth,
                               json={'meeting_url': url, 'consent': True})
        assert response.status_code == 422, url
        detail = response.json()['detail']
        assert detail['code'] == 'unsupported_platform'
        assert detail['message'] == 'Only Google Meet links (meet.google.com) are supported.'
    # The fourth dispatch in a minute is refused by the per-IP bot limit.
    limited = client.post(f'/api/meetings/{meeting_id}/bot', headers=auth,
                          json={'meeting_url': 'http://meet.google.com/abc-defg-hij', 'consent': True})
    assert limited.status_code == 429


def test_bot_requires_consent_before_any_url_check():
    meeting_id, auth = _new_meeting()
    response = client.post(f'/api/meetings/{meeting_id}/bot', headers=auth,
                           json={'meeting_url': 'https://meet.google.com/abc-defg-hij', 'consent': False})
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'bad_request'


def test_simulated_bot_accepts_a_meet_link_and_stays_labelled():
    meeting_id, auth = _new_meeting()
    response = client.post(f'/api/meetings/{meeting_id}/bot', headers=auth,
                           json={'meeting_url': 'https://meet.google.com/abc-defg-hij?authuser=0', 'consent': True})
    assert response.status_code == 200
    assert response.json()['backend'] == 'simulated'
    assert 'does not join a real meeting' in response.json()['label']
