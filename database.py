import json
import os
from typing import List, Dict

DATA_FILE = 'data.json'

def init_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f)

def load_user_data(user_id: int) -> Dict:
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
        return data.get(str(user_id), {'urls': [], 'settings': {'notify_down': True, 'notify_up': True}})

def save_user_data(user_id: int, user_data: Dict):
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    data[str(user_id)] = user_data
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def add_url(user_id: int, url: str):
    user_data = load_user_data(user_id)
    if url not in user_data['urls']:
        user_data['urls'].append(url)
        save_user_data(user_id, user_data)
        return True
    return False

def remove_url(user_id: int, url: str):
    user_data = load_user_data(user_id)
    if url in user_data['urls']:
        user_data['urls'].remove(url)
        save_user_data(user_id, user_data)
        return True
    return False

def get_urls(user_id: int) -> List[str]:
    return load_user_data(user_id)['urls']

def get_all_users() -> List[int]:
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
        return [int(user_id) for user_id in data.keys()]
