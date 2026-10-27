"""Concurrency checks for the manual chat API.

    python load_test.py http http://localhost:8000   # parallel /codes, /search, /ask and uploads
    python load_test.py sdk manuals                  # cursor() streaming vs collect(), cursor + concurrent insert

Model cost (http mode): one embedding call per /search, one embedding + one gpt-4o-mini call per /ask,
one embedding batch per uploaded manual.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).parent
MANUALS = HERE / 'data' / 'manuals'

SEARCHES = ['hydraulic oil capacity', 'spindle overheat', 'descale the wash arms', 'condensate drain', 'defrost interval',
            'overload sensor limit', 'coolant mix ratio', 'booster heater power', 'oil separator pressure drop', 'door gasket part']
ASKS = ['What does ALM-3 mean on the router?', 'How much oil does the compressor hold?', 'What wind speed stops the lift outdoors?',
        'What should I do when the dishwasher shows F8?', 'At what temperature does the freezer alarm sound?', 'What collet does the spindle use?']
CODES = ['E01', 'E07', 'E12', 'E18', 'ALM-3', 'ALM-9', 'ALM-14', 'F2', 'F5', 'F8', 'A1', 'A3', 'A6']


def timed(fn, *a):
    t0 = time.perf_counter()
    r = fn(*a)
    return time.perf_counter() - t0, r


def run_batch(name, fn, args, concurrency):
    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(concurrency) as ex:
        results = list(ex.map(lambda a: timed(fn, a), args))
    wall = time.perf_counter() - t0
    lat = sorted(r[0] for r in results)
    ok = sum(1 for r in results if r[1])
    p95 = lat[max(0, int(len(lat) * 0.95) - 1)]
    print(json.dumps({'test': name, 'n': len(args), 'concurrency': concurrency, 'ok': ok, 'wall_s': round(wall, 2),
                      'req_per_s': round(len(args) / wall, 1), 'p50_s': round(statistics.median(lat), 2), 'p95_s': round(p95, 2)}))
    return results


def http_mode(base: str, headers: dict) -> None:
    c = httpx.Client(base_url=base, headers=headers, timeout=120)

    def code(cd):
        r = c.get('/codes', params={'code': cd})
        return r.status_code == 200 and len(r.json()['rows']) >= 1

    def search(q):
        r = c.get('/search', params={'q': q, 'k': 3})
        return r.status_code == 200 and len(r.json()['rows']) == 3

    def ask(q):
        r = c.post('/ask', json={'question': q, 'equipment': None, 'asked_by': 'load-test'})
        return r.status_code == 200 and bool(r.json().get('answer'))

    def upload(i):
        src = sorted(MANUALS.glob('*.pdf'))[i % 4]
        with open(src, 'rb') as f:
            r = c.post('/manuals', data={'manual_id': f'lt-{int(time.time())}-{i}', 'equipment': f'load test copy {i}', 'vendor': 'lt'},
                       files={'doc': (src.name, f, 'application/pdf')})
        return r.status_code == 200

    run_batch('codes (no model calls)', code, CODES * 8, 16)
    run_batch('search (1 embedding each)', search, SEARCHES * 3, 8)
    run_batch('ask (embedding + gpt-4o-mini each)', ask, ASKS * 2, 4)
    run_batch('upload manuals (1 embedding batch each)', upload, list(range(6)), 6)


def sdk_mode(target: str) -> None:
    import pixeltable as pxt

    from app import Chunks, Manuals, TableModel

    TableModel.bind_all(target)
    t0 = time.perf_counter()
    rows = Chunks.select(Chunks.manual_id, Chunks.text).collect()
    t_collect = time.perf_counter() - t0
    t0 = time.perf_counter()
    n = 0
    with Chunks.select(Chunks.manual_id, Chunks.text).cursor() as cur:
        for _ in cur:
            n += 1
    t_cursor = time.perf_counter() - t0
    print(json.dumps({'test': 'collect vs cursor', 'rows_collect': len(rows), 'rows_cursor': n,
                      'collect_s': round(t_collect, 3), 'cursor_s': round(t_cursor, 3)}))

    # early break releases the cursor
    with Chunks.select(Chunks.text).cursor() as cur:
        first = next(iter(cur))
    print(json.dumps({'test': 'cursor early break', 'first_len': len(first['text'])}))

    # open a cursor, then insert a manual from another process while it is still open
    child = (
        'import time, sys; sys.path.insert(0, "."); from app import Manuals, TableModel; '
        f'TableModel.bind_all({target!r}); t=time.perf_counter(); '
        'Manuals.insert([{"manual_id": f"cur-{int(time.time())}", "equipment": "cursor test", "vendor": None, '
        '"doc": "data/manuals/rc14-freezer.md"}]); print(round(time.perf_counter()-t, 2))'
    )
    with Manuals.select(Manuals.manual_id).cursor() as cur:
        it = iter(cur)
        first = next(it)
        t0 = time.perf_counter()
        p = subprocess.Popen([sys.executable, '-c', child], cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            out, _ = p.communicate(timeout=20)
            state = 'insert finished while cursor open'
        except subprocess.TimeoutExpired:
            state = 'insert blocked >20 s while cursor open'
            out = None
        rest = sum(1 for _ in it)
    if out is None:
        out, _ = p.communicate(timeout=120)
    print(json.dumps({'test': 'cursor + concurrent insert', 'state': state, 'insert_s': out.strip() if out else None,
                      'rows_seen_by_cursor': 1 + rest, 'wait_s': round(time.perf_counter() - t0, 2)}))
    print(json.dumps({'test': 'counts', 'manuals': Manuals.count(), 'chunks': Chunks.count()}))


if __name__ == '__main__':
    mode, arg = sys.argv[1], sys.argv[2]
    if mode == 'http':
        import os
        key = os.environ.get('PIXELTABLE_API_KEY') if len(sys.argv) > 3 and sys.argv[3] == '--cloud' else None
        http_mode(arg, {'X-api-key': key} if key else {})
    else:
        sdk_mode(arg)
