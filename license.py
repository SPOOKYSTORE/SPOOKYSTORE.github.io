"""
server.py  -  Spookystore license validation server

Setup:
  pip install flask
  python server.py

Workflow:
  1. Generate keys on keys.html (admin panel)
  2. Click "Export JSON" — save as keys.json next to this server.py
  3. Run the server — it reads keys.json on every request
  4. To add more keys: export again from admin panel, replace keys.json

Set ADMIN_SECRET before deploying.
"""

import json
import os
from datetime import date
from flask import Flask, request, jsonify

app = Flask(__name__)

KEYS_FILE    = os.path.join(os.path.dirname(__file__), 'keys.json')
ADMIN_SECRET = 'spooky2025'   # ← change this


def load_keys():
    try:
        with open(KEYS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f'Error loading keys: {e}')
        return []


def save_keys(keys):
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)


def is_expired(key_obj):
    if key_obj.get('expires') == 'Never':
        return False
    try:
        return date.fromisoformat(key_obj['expires']) < date.today()
    except Exception:
        return False


# ── validate (called by license.py in the bot) ────────────────────────────────
@app.route('/validate', methods=['POST'])
def validate():
    data  = request.get_json(silent=True) or {}
    key   = str(data.get('key', '')).strip().upper()

    if not key:
        return jsonify({'valid': False, 'message': 'no key provided'})

    match = next((k for k in load_keys() if k['key'] == key), None)

    if not match:
        return jsonify({'valid': False, 'message': 'invalid key'})
    if is_expired(match):
        return jsonify({'valid': False, 'message': f"key expired on {match.get('expires')}"})

    return jsonify({'valid': True, 'plan': match.get('plan','unknown'), 'expires': match.get('expires')})


# ── admin: import bulk JSON exported from keys.html ───────────────────────────
@app.route('/admin/import', methods=['POST'])
def admin_import():
    if request.headers.get('X-Admin-Secret') != ADMIN_SECRET:
        return jsonify({'ok': False, 'message': 'unauthorized'}), 403
    data = request.get_json(silent=True) or []
    if not isinstance(data, list):
        return jsonify({'ok': False, 'message': 'expected JSON array'})
    save_keys(data)
    return jsonify({'ok': True, 'count': len(data)})


# ── admin: add single key ─────────────────────────────────────────────────────
@app.route('/admin/add', methods=['POST'])
def admin_add():
    if request.headers.get('X-Admin-Secret') != ADMIN_SECRET:
        return jsonify({'ok': False, 'message': 'unauthorized'}), 403
    data = request.get_json(silent=True) or {}
    key_obj = {
        'key':     str(data.get('key','')).strip().upper(),
        'plan':    data.get('plan','monthly'),
        'expires': data.get('expires',''),
        'created': data.get('created', str(date.today())),
        'note':    data.get('note',''),
    }
    if not key_obj['key']:
        return jsonify({'ok': False, 'message': 'no key'})
    keys = load_keys()
    if any(k['key'] == key_obj['key'] for k in keys):
        return jsonify({'ok': False, 'message': 'key already exists'})
    keys.insert(0, key_obj)
    save_keys(keys)
    return jsonify({'ok': True, 'key': key_obj['key']})


# ── admin: list all keys ──────────────────────────────────────────────────────
@app.route('/admin/keys', methods=['GET'])
def admin_keys():
    if request.headers.get('X-Admin-Secret') != ADMIN_SECRET:
        return jsonify({'ok': False, 'message': 'unauthorized'}), 403
    return jsonify(load_keys())


# ── health ─────────────────────────────────────────────────────────────────────
@app.route('/', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'spookystore'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)