#!/usr/bin/env python3
"""Insert push-to-github route into app.py"""
import re

with open('/root/umkm-copilot/app.py', 'r') as f:
    content = f.read()

# Check if route already exists
if 'def push_to_github' in content:
    print("Route already exists!")
    exit(0)

# Find the insertion point
marker = "@app.route('/debug/whatsapp')"
if marker not in content:
    print("Marker not found!")
    exit(1)

# Read the HTML template from file
with open('/root/umkm-copilot/push_template.html', 'r') as f:
    html = f.read()

# Build the route
route = '''
@app.route('/push-to-github', methods=['GET', 'POST'])
def push_to_github():
    """Push to GitHub via browser"""
    import urllib.request as _urlreq
    import urllib.error as _urlerr
    from concurrent.futures import ThreadPoolExecutor
    import base64 as _b64

    if request.method == 'GET':
        return \'\'' + html + '\'\\'\\'

    token = (request.form.get('github_token') or '').strip()
    if not token:
        return jsonify(success=False, error='Token kosong'), 400

    owner, repo_name = 'mjfendin', 'UMKM-COPILOT'
    API = 'https://api.github.com'

    def _gh(method, path, data=None):
        url = f'{API}{path}'
        hdrs = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'UMKM-Copilot'}
        body = json.dumps(data).encode() if data else None
        req = _urlreq.Request(url, data=body, headers=hdrs, method=method)
        try:
            with _urlreq.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except _urlerr.HTTPError as e:
            return {'error': f'HTTP {e.code}: {e.read().decode()[:300]}'}
        except Exception as e:
            return {'error': str(e)}

    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.dirname(here)
    skip_dirs = {'.git', '__pycache__', '.hermes', 'node_modules', '.vercel', 'venv', '.venv', '.cache', 'instance', 'static/gen'}
    skip_ext = ('.pyc', '.pyo', '.db', '.zip', '.bundle')
    file_list = []

    for dp, dns, fns in os.walk(proj):
        dns[:] = [d for d in dns if d not in skip_dirs and not d.startswith('.')]
        for fn in fns:
            if fn.startswith('.') or fn.endswith(skip_ext): continue
            fp = os.path.join(dp, fn)
            rp = os.path.relpath(fp, proj)
            try:
                raw = open(fp, 'rb').read()
                if len(raw) > 1_500_000: continue
                raw.decode('utf-8')
                file_list.append((rp, _b64.b64encode(raw).decode()))
            except (UnicodeDecodeError, IOError): pass

    if not file_list:
        return jsonify(success=False, error='No files found'), 400

    ref = _gh('GET', f'/repos/{owner}/{repo_name}/git/refs/heads/main')
    branch = 'main'
    if 'error' in ref:
        ref = _gh('GET', f'/repos/{owner}/{repo_name}/git/refs/heads/master')
        branch = 'master'
    if 'error' in ref:
        return jsonify(success=False, error=f'Repo error: {ref.get("error")}')
    base_sha = ref['object']['sha']

    def _mkblob(item):
        rp, b64c = item
        return rp, _gh('POST', f'/repos/{owner}/{repo_name}/git/blobs', {'content': b64c, 'encoding': 'base64'})

    tree_items, uploaded, errors = [], 0, []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for rp, res in pool.map(_mkblob, file_list):
            if 'sha' in res:
                tree_items.append({'path': rp, 'mode': '100644', 'type': 'blob', 'sha': res['sha']})
                uploaded += 1
            else:
                errors.append(f'{rp}: {res.get("error","?")}')

    tree = _gh('POST', f'/repos/{owner}/{repo_name}/git/trees', {'tree': tree_items, 'base_tree': base_sha})
    if 'sha' not in tree:
        return jsonify(success=False, error=f'Tree failed: {tree.get("error")}')

    commit = _gh('POST', f'/repos/{owner}/{repo_name}/git/commits', {'message': f'Web push: {uploaded} files', 'tree': tree['sha'], 'parents': [base_sha]})
    if 'sha' not in commit:
        return jsonify(success=False, error=f'Commit failed: {commit.get("error")}')

    _gh('PATCH', f'/repos/{owner}/{repo_name}/git/refs/heads/{branch}', {'sha': commit['sha'], 'force': False})

    return jsonify(success=True, files_uploaded=uploaded, commit_sha=commit['sha'][:7], errors=errors[:5], repo_url=f'https://github.com/{owner}/{repo_name}')

'''

content = content.replace(marker, route + marker)

with open('/root/umkm-copilot/app.py', 'w') as f:
    f.write(content)

print("Route inserted successfully!")
