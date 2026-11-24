import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SOURCE = 'https://raw.githubusercontent.com/4lwayz/portwatch-vi/main/data/tracker.json'
SITE = 'https://portwatch-vi.xyz/'
STATE = Path('relay-state.json')
COLORS = {'up': 0x2ecc71, 'down': 0xe74c3c, 'removed': 0xe74c3c,
          'claim': 0xf1c40f, 'flag': 0xf39c12, 'new': 0x3498db}

def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def load_tracker():
    req = Request(SOURCE, headers={'User-Agent': 'PortWatch-Discord-Relay/1.0', 'Cache-Control': 'no-cache'})
    with urlopen(req, timeout=30) as response:
        data = json.load(response)
    if not isinstance(data.get('news'), list) or not isinstance(data.get('changes'), list):
        raise ValueError('Unexpected tracker schema')
    return data

def events(data):
    out = {}
    for entry in data['changes']:
        kind = str(entry.get('kind', 'update'))
        # The scout's change history is oldest first.
        key = 'change:' + digest(entry)
        out[key] = (digest(entry), {'title': 'Tracker: ' + kind.capitalize(),
            'description': str(entry.get('text', ''))[:4000], 'url': SITE,
            'color': COLORS.get(kind, 0x5865f2), 'footer': {'text': 'PortWatch VI | ' + str(entry.get('date', ''))}})
    for item in reversed(data['news']):
        ident = item['id']
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', ident):
            continue
        embed = {'title': str(item.get('title', 'News'))[:256],
                 'description': str(item.get('dek', ''))[:4000],
                 'url': SITE + 'news/' + ident, 'color': 0x9b59b6,
                 'footer': {'text': 'PortWatch VI | ' + str(item.get('category', 'News')) + ' | ' + str(item.get('updatedAt', item.get('date', '')))}}
        # Fingerprint editorial content, not image or incidental metadata.
        version = digest({k: item.get(k) for k in ('title', 'dek', 'body', 'updatedAt')})
        out['news:' + ident] = (version, embed)
    return out

def save(state):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    tmp.replace(STATE)

def send(webhook, embed):
    payload = json.dumps({'username': 'PortWatch VI', 'embeds': [embed], 'allowed_mentions': {'parse': []}}).encode()
    for attempt in range(5):
        req = Request(webhook + '?wait=true', data=payload, headers={'Content-Type': 'application/json', 'User-Agent': 'PortWatch-Discord-Relay/1.0'})
        try:
            with urlopen(req, timeout=30) as response:
                if 200 <= response.status < 300:
                    return
                raise RuntimeError('Discord returned unexpected status')
        except HTTPError as exc:
            if exc.code == 429 and attempt < 4:
                try:
                    delay = float(json.load(exc).get('retry_after', 1))
                except (ValueError, TypeError):
                    delay = 2
                time.sleep(max(1, min(delay, 60)))
                continue
            # Never print an exception containing the webhook URL.
            raise RuntimeError(f'Discord HTTP {exc.code}') from None
        except (URLError, TimeoutError):
            # Ambiguous delivery: do not retry within this run.
            raise RuntimeError('Discord connection failed; delivery uncertain') from None
    raise RuntimeError('Discord rate limit retry exhausted')

def main():
    webhook = os.environ.get('DISCORD_WEBHOOK_URL', '').strip()
    if not re.fullmatch(r'https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+', webhook):
        raise ValueError('Set DISCORD_WEBHOOK_URL to your Discord webhook URL (without query parameters)')
    current = events(load_tracker())
    if not STATE.exists():
        send(webhook, {'title': 'PortWatch VI relay online', 'description': 'Monitoring published news and tracker changes. Existing entries have been recorded; future updates will be posted here.', 'url': SITE, 'color': 0x2ecc71})
        save({key: version for key, (version, _) in current.items()})
        print('Baseline saved; relay online message sent.')
        return
    state = json.loads(STATE.read_text(encoding='utf-8'))
    sent = 0
    for key, (version, embed) in current.items():
        if state.get(key) == version:
            continue
        if key.startswith('news:') and key in state:
            embed = {**embed, 'title': ('Updated: ' + embed['title'])[:256]}
        send(webhook, embed)
        state[key] = version
        save(state)
        sent += 1
        time.sleep(0.5)
    print(f'{sent} new or revised items sent.')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # All known webhook errors are sanitized by send(). Unexpected errors
        # are logged by type only, so no credential can leak into action logs.
        print('Relay failed: ' + (str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__), file=sys.stderr)
        sys.exit(1)
