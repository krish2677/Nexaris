import requests
BASE = 'http://localhost:8000/api/v1'

# Login
r = requests.post(f'{BASE}/auth/login', json={'email': 'arena@test.com', 'password': 'test1234'})
print(f'Login: {r.status_code}')
if r.status_code != 200:
    print(r.text[:200])
    exit(1)

token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

endpoints = [
    '/campaigns/active',
    '/treasury/balance',
    '/user/rankings',
    '/wallet/history',
]

for path in endpoints:
    try:
        resp = requests.get(f'{BASE}{path}', headers=h, timeout=10)
        body = resp.json()
        keys = list(body.keys()) if isinstance(body, dict) else type(body).__name__
        print(f'  {resp.status_code} {path} -> {keys}')
    except Exception as e:
        print(f'  ERR {path} -> {e}')

print('ALL ENDPOINTS TESTED')
