"""Opaque campaign links and private aggregate counts; no visitor profiling.

Only immutable, provider-accepted email plans can record requests. Shared copies,
scanners and repeat requests are deliberately not interpreted as athlete visits.
Plain-text fallback preserves the reviewed copy and its original direct URLs.
"""
import hashlib
import html
import re
import secrets

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import RedirectResponse

router = APIRouter()
TARGETS = {'website': 'https://recdebut.com/',
           'registration': 'https://recdebut.com/all-registration/',
           'video': 'https://youtu.be/YJoPHIWmvnQ'}
SOURCE_URLS = {
    **{scheme + host + tail: 'website' for scheme in ('http://', 'https://', '')
       for host in ('recdebut.com', 'www.recdebut.com') for tail in ('', '/')},
    **{scheme + host + tail: 'registration' for scheme in ('http://', 'https://')
       for host in ('recdebut.com', 'www.recdebut.com')
       for tail in ('/all-registration', '/all-registration/')},
    'https://youtu.be/YJoPHIWmvnQ': 'video'}
URLS = re.compile(r'https?://[^\s<>]+|www\.[^\s<>]+', re.I)
NOTICE = ('Counts are HTML email link requests after provider acceptance. Shared copies, '
          'automated checks and repeat requests can contribute. They do not establish visitor '
          'identity, human visits, email opens, delivery or registrations. Plain-text direct URLs '
          'and browsing within recdebut.com are not measured here.')


def delivery():
    import recdebut_delivery
    return recdebut_delivery


def schema(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS recdebut_campaign_links (
            token_sha256 TEXT PRIMARY KEY, plan_id TEXT NOT NULL, person_id TEXT NOT NULL,
            target TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(plan_id,person_id,target));
        CREATE TABLE IF NOT EXISTS recdebut_campaign_link_counts (
            token_sha256 TEXT PRIMARY KEY, request_count INTEGER NOT NULL,
            first_requested_at TEXT NOT NULL, last_requested_at TEXT NOT NULL);
    ''')


def render(db, plan_id, profile, item):
    """Keep visible wording intact; allowlisted destinations are sealed in the plan."""
    w = delivery().workflow()
    links = {}
    chunks, start = [], 0
    for match in URLS.finditer(item['message']):
        raw = match.group().rstrip('.,;:!?)}]\"\'’”')
        target = SOURCE_URLS.get(raw)
        url = None
        if target:
            if target not in links:
                token = secrets.token_urlsafe(32)
                links[target] = profile['unsubscribe_base'] + '/api/v1/recdebut/workflow/links/' + token
                db.execute('INSERT INTO recdebut_campaign_links VALUES(?,?,?,?,?)',
                           (hashlib.sha256(token.encode()).hexdigest(), plan_id, item['person_id'], target, w.now()))
            url = links[target]
        elif raw == item['unsubscribe_url']:
            url = raw
        chunks.append(html.escape(item['message'][start:match.start()]))
        label = html.escape(raw)
        chunks.append('<a href="' + html.escape(url, quote=True) + '" rel="noreferrer">' + label + '</a>' if url else label)
        start = match.start() + len(raw)
    chunks.append(html.escape(item['message'][start:]))
    item['campaign_links'] = links
    item['campaign_destinations'] = {key: TARGETS[key] for key in links}
    item['html_message'] = '<!doctype html><html><body><p>' + ''.join(chunks).replace('\n', '<br>\n') + '</p></body></html>'


@router.get('/links/{token}')
def campaign_link(token: str):
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise HTTPException(404, 'Link not found.')
    d = delivery(); w = d.workflow()
    hashed = hashlib.sha256(token.encode()).hexdigest()
    with w.connect() as db:
        d.schema(db); db.execute('BEGIN IMMEDIATE')
        link = db.execute('SELECT * FROM recdebut_campaign_links WHERE token_sha256=?', (hashed,)).fetchone()
        if not link or link['target'] not in TARGETS:
            raise HTTPException(404, 'Link not found.')
        try:
            _, plan = d.load_plan(db, link['plan_id'])
            item = next((r for r in plan['recipients'] if r['person_id'] == link['person_id']), None)
            expected_url = plan['sender']['unsubscribe_base'] + '/api/v1/recdebut/workflow/links/' + token
            if (plan['channel'] != 'email' or not item
                    or item.get('campaign_links', {}).get(link['target']) != expected_url
                    or item.get('campaign_destinations', {}).get(link['target']) != TARGETS[link['target']]):
                raise ValueError('Unbound campaign link')
            destination = item['campaign_destinations'][link['target']]
            key = w.digest({'draft_id': plan['draft_id'], 'channel': 'email', 'destination': item['destination']})
            accepted = db.execute("SELECT 1 FROM recdebut_send_attempts WHERE dedup_key=? AND plan_id=? AND person_id=? AND state='ACCEPTED'",
                                  (key, plan['id'], item['person_id'])).fetchone()
            if not accepted: raise ValueError('No accepted recipient attempt')
        except (HTTPException, ValueError, KeyError, TypeError):
            raise HTTPException(404, 'Link not found.')
        stamp = w.now()
        db.execute('''INSERT INTO recdebut_campaign_link_counts VALUES(?,1,?,?)
            ON CONFLICT(token_sha256) DO UPDATE SET request_count=request_count+1,last_requested_at=excluded.last_requested_at''',
                   (hashed, stamp, stamp))
    return RedirectResponse(destination, status_code=302,
                            headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})


@router.get('/traffic')
def traffic(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    d = delivery(); w = d.workflow()
    with w.connect() as db:
        d.schema(db)
        total = db.execute('SELECT COALESCE(SUM(request_count),0) FROM recdebut_campaign_link_counts').fetchone()[0]
        rows = db.execute('''SELECT l.plan_id,l.target,SUM(c.request_count) AS requests,
            COUNT(*) AS distinct_links,MIN(c.first_requested_at) AS first_requested_at,
            MAX(c.last_requested_at) AS last_requested_at
            FROM recdebut_campaign_links l JOIN recdebut_campaign_link_counts c USING(token_sha256)
            GROUP BY l.plan_id,l.target ORDER BY last_requested_at DESC LIMIT 200''').fetchall()
        campaigns = []
        for row in rows:
            try:
                _, plan = d.load_plan(db, row['plan_id'])
            except (HTTPException, ValueError, KeyError, TypeError):
                continue
            campaigns.append({**dict(row), 'title': plan['subject'], 'draft_id': plan['draft_id']})
    return {'total_requests': total, 'campaigns': campaigns, 'group_limit': 200,
            'tracking_configured': bool(d.sender_profile('email').get('track_links')), 'notice': NOTICE}
