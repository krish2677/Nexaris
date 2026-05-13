import urllib.request
req = urllib.request.Request('https://nexaris-750648121075.europe-west1.run.app/api/v1/download/apk', method='GET')
try:
    with urllib.request.urlopen(req) as response:
        print(response.getcode())
        print(response.headers)
        data = response.read(1024)
        print('First bytes:', data[:4])
except Exception as e:
    print(e)
