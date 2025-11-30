import requests
import json

BASE_URL = "https://omss-2ccc6-default-rtdb.firebaseio.com/"

def read(path):
    url = f"{BASE_URL}{path}.json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def push(path, data):
    url = f"{BASE_URL}{path}.json"
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Firebase Push Failed: {response.text}")

def update(path, data):
    url = f"{BASE_URL}{path}.json"
    response = requests.patch(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Firebase Update Failed: {response.text}")
