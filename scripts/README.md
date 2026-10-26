# scripts

Standard-library-first helpers. Nothing here needs the app to be running except `ping.py`.

| Script | What it does |
|---|---|
| `check.py` | Repository checks: required files, no template markers, no `dangerouslySetInnerHTML`, no stray `console.log`, no obvious hard-coded credentials, and every category PNG (size, long edge, alpha, matching A/B canvas). `--strict` adds the security and logging checks. |
| `ping.py` | Fetches `/health` from a deployed or local API and exits non-zero unless at least one provider is ready. Usage: `python scripts/ping.py http://127.0.0.1:8000`. |
| `keyout.py` | Rebuilds the category frames from `raw/` into `frontend/public/assets/categories/`: 768 px long edge, transparent background, ≤400 KB, one shared canvas and one colour depth per A/B pair. |

```powershell
python scripts/check.py --strict
python scripts/ping.py http://127.0.0.1:8000
pip install -r scripts/requirements.txt   # only for keyout.py (Pillow, numpy)
python scripts/keyout.py --all raw frontend/public/assets/categories
```
