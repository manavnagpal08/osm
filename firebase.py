import requests

FIREBASE_URL = "https://omss-2ccc6-default-rtdb.firebaseio.com/"

def read(path):
    url = f"{FIREBASE_URL}{path}.json"
    res = requests.get(url)
    return res.json()

def save(path, data):
    url = f"{FIREBASE_URL}{path}.json"
    res = requests.put(url, json=data)
    return res.json()

def update(path, data):
    url = f"{FIREBASE_URL}{path}.json"
    res = requests.patch(url, json=data)
    return res.json()

def push(path, data):
    url = f"{FIREBASE_URL}{path}.json"
    res = requests.post(url, json=data)
    return res.json()

