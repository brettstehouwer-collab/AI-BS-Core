"""Synthetic private inbox and immutable timeline acceptance; no provider calls."""
import json
from test_recdebut_workflow import client, save, BASE
import recdebut_workflow as w


def receipt(c, event='event1', family='family1'):
    save(c, 'family', family, {'name': 'Synthetic ' + family})
    with w.connect() as db:
        db.execute('INSERT INTO recdebut_registration_receipts VALUES(?,?,?,?)', (event, 'a'*64, family, w.now()))


def review(c, event='event1', **kwargs):
    return c.put(BASE + f'/registrations/{event}/review', json={'actor': 'Synthetic staff', 'revision': 0, 'status': 'accepted', **kwargs})


def test_empty_private_inbox(client):
    r = client.get(BASE + '/registrations')
    assert r.status_code == 200 and r.headers['cache-control'] == 'no-store'
    assert r.json() == {'registrations': [], 'sending_enabled': False}


def test_review_persists_and_rejects_stale(client):
    receipt(client)
    assert review(client, notes='Reviewed without communication').status_code == 200
    assert review(client, status='pending').status_code == 409
    r = client.get(BASE + '/registrations').json()['registrations'][0]
    assert r['revision'] == 1 and r['status'] == 'accepted'
    entries = client.get(BASE + '/families/family1/timeline').json()['entries']
    assert entries[0]['details']['notes'] == 'Reviewed without communication'
    assert entries[0]['actor'] == 'Synthetic staff'


def test_duplicate_preserves_originals_and_links_evidence(client):
    receipt(client)
    save(client, 'family', 'family2', {'name': 'Retained family'})
    before = client.get(BASE).json()['records']
    assert review(client, status='duplicate', target_family_id='family2').status_code == 200
    assert client.get(BASE).json()['records'] == before
    assert client.get(BASE + '/families/family2/timeline').json()['entries'][0]['action'] == 'duplicate_registration_linked'
    with w.connect() as db:
        assert db.execute('SELECT family_id FROM recdebut_registration_receipts').fetchone()[0] == 'family1'


def test_invalid_duplicate_and_chains(client):
    receipt(client)
    assert review(client, status='duplicate', target_family_id='family1').status_code == 422
    assert review(client, status='duplicate', target_family_id='missing').status_code == 422
    assert review(client, target_family_id='family1').status_code == 422
    receipt(client, 'event2', 'family2')
    save(client, 'family', 'family3', {'name': 'Third family'})
    assert review(client, status='duplicate', target_family_id='family2').status_code == 200
    assert review(client, 'event2', status='duplicate', target_family_id='family3').status_code == 409


def test_timeline_snapshots_paging_and_validation(client):
    save(client, 'family', 'family1', {'name': 'Original'})
    save(client, 'family', 'family1', {'name': 'Updated'}, revision=1)
    url = BASE + '/families/family1/timeline'
    assert client.post(url, json={'actor': 'Staff', 'text': 'Internal only'}).status_code == 200
    first = client.get(url + '?limit=2').json()
    older = client.get(url + '?limit=2&before=' + str(first['next_before'])).json()
    assert len(first['entries']) == 2 and len(older['entries']) == 1
    assert older['entries'][0]['details']['record']['name'] == 'Original'
    assert first['entries'][0]['details']['text'] == 'Internal only'
    assert client.get(url + '?limit=101').status_code == 422
    assert client.post(url, json={'actor': ' ', 'text': 'x'}).status_code == 422
    assert client.post(url, json={'actor': 'Staff', 'text': ' '}).status_code == 422
    assert client.get(BASE + '/families/missing/timeline').status_code == 404
    assert review(client, event='missing').status_code == 404


def test_unauthorized_access(client):
    client.app.dependency_overrides.clear()
    assert client.get(BASE + '/registrations').status_code == 403
    assert client.get(BASE + '/families/family1/timeline').status_code == 403
    assert review(client).status_code == 403


def test_relink_retains_prior_family_history(client):
    save(client, 'family', 'family1', {'name': 'Original'})
    save(client, 'family', 'family2', {'name': 'Other'})
    save(client, 'person', 'person1', {'name': 'Contact', 'family_id': 'family1'})
    save(client, 'person', 'person1', {'name': 'Contact', 'family_id': 'family2'}, revision=1)
    assert client.get(BASE + '/families/family1/timeline').json()['entries'][0]['action'] == 'record_relinked'
