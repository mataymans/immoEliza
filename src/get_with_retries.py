import random
import time
import requests


def get_with_retries(url, headers, session=None, retries=5, timeout=30):
    sess = session or requests.Session()
    last = None

    for i in range(retries):
        try:
            r = sess.get(url, headers=headers, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.0 + random.random() * (i + 1))
                last = r
                continue
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(1.0 + random.random() * (i + 1))

    return None