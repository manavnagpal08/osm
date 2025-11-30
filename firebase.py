import requests

BASE_URL = "https://omss-2ccc6-default-rtdb.firebaseio.com/"

def read(path):
    url = f"{BASE_URL}{path}.json"
    res = requests.get(url)
    if res.status_code == 200:
        return res.json()
    return None

def push(path, data):
    url = f"{BASE_URL}{path}.json"
    res = requests.post(url, json=data)
    if res.status_code == 200:
        return res.json()
    raise Exception(f"Push failed: {res.text}")

def update(path, data):
    url = f"{BASE_URL}{path}.json"
    res = requests.patch(url, json=data)
    if res.status_code == 200:
        return res.json()
    raise Exception(f"Update failed: {res.text}")
