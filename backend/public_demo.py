"""Small, single-process public demo limits; no model credentials reach clients."""
import os
import secrets
import threading
import time
from collections import deque
from contextlib import contextmanager
from fastapi import HTTPException


def public_demo():
    return os.getenv('PUBLIC_DEMO', 'false').lower() == 'true'


def error(code, message, status=429):
    raise HTTPException(status, {'code': code, 'message': message}, headers={'Retry-After': '60'} if status == 429 else None)


class RequestLimiter:
    def __init__(self):
        self.lock = threading.Lock()
        self.buckets = {}

    def allow(self, owner):
        now = time.monotonic()
        with self.lock:
            self.buckets = {k:v for k,v in self.buckets.items() if v and v[-1] > now-60}
            keys = [('global', int((os.getenv('MAX_REQUESTS_PER_MINUTE') or '300'))),
                    (owner, int((os.getenv('MAX_SESSION_REQUESTS_PER_MINUTE') or '90')))]
            for key, limit in keys:
                bucket = self.buckets.setdefault(key, deque())
                while bucket and bucket[0] <= now-60: bucket.popleft()
                if len(bucket) >= limit: return False
            for key, _ in keys: self.buckets[key].append(now)
            return True


limiter = RequestLimiter()
# The supported deployment runs exactly one Uvicorn worker and one service instance.
# Fail fast instead of queuing unbounded paid requests.
live_slot = threading.BoundedSemaphore(1)


@contextmanager
def inference_access(mode, supplied_token):
    if mode != 'live':
        yield
        return
    expected = os.getenv('LIVE_DEMO_TOKEN', '')
    if public_demo() or expected:
        if len(expected) < 32:
            error('LIVE_UNAVAILABLE', 'Protected live access is not configured. Use Synthetic or open a historical packet.', 503)
        if not supplied_token or not secrets.compare_digest(supplied_token, expected):
            error('LIVE_PROTECTED', 'A live access key is required for live AMD inference.', 403)
    if not live_slot.acquire(blocking=False):
        error('LIVE_BUSY', 'Another live request is running. Wait for it to finish before retrying.')
    try:
        yield
    finally:
        live_slot.release()
