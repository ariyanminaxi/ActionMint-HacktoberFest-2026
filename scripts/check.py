from __future__ import annotations
import argparse
import struct
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
REQUIRED=[
 "README.md","LICENSE",".gitignore","backend/.env.example","THIRD_PARTY_NOTICES.md",
 "frontend/package.json","frontend/pnpm-lock.yaml","frontend/index.html","frontend/public/assets/actionmint-mark.png",
 "frontend/public/_headers","frontend/src/App.tsx","frontend/src/features/meeting/categories.ts",
 "backend/app/main.py","backend/requirements.txt","backend/data/questions.md","backend/tests/test_api.py",
 "model/.env.model.example","render.yaml","supabase/migrations/0001_meetings_saved.sql","scripts/ping.py",
 "scripts/requirements.txt",
]
CATEGORY_IDS=["overview","decisions","actions","people","timeline","flow","transcript","ask","recap","history"]
ASSET_DIR=ROOT/"frontend/public/assets/categories"
MAX_ASSET_BYTES=400*1024
LONG_EDGE=768

def png_info(path: Path) -> dict:
    """Read IHDR/alpha information from a PNG without third-party libraries."""
    data=path.read_bytes()
    if data[:8]!=b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    offset=8
    info={"has_alpha":False}
    while offset+8<=len(data):
        length,kind=struct.unpack(">I4s",data[offset:offset+8])
        body=data[offset+8:offset+8+length]
        if kind==b"IHDR":
            width,height,depth,color=struct.unpack(">IIBB",body[:10])
            info.update(width=width,height=height,depth=depth,color=color)
            # colour type 4 = grey+alpha, 6 = RGBA
            info["has_alpha"]=color in (4,6)
        elif kind==b"tRNS":
            info["has_alpha"]=True
        offset+=12+length
        if kind==b"IDAT":
            break
    if "width" not in info:
        raise ValueError("no IHDR")
    return info

def check_category_assets() -> tuple[list[str],list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for category_id in CATEGORY_IDS:
        boxes=[]
        for frame in ("a","b"):
            asset=ASSET_DIR/f"{category_id}-{frame}.png"
            rel=asset.relative_to(ROOT)
            if not asset.is_file():
                warnings.append(f"Optional category frame is missing: {rel} (fallback glyph active)")
                continue
            try:
                info=png_info(asset)
            except ValueError as exc:
                errors.append(f"{rel}: unreadable PNG ({exc})")
                continue
            size=asset.stat().st_size
            if size>MAX_ASSET_BYTES:
                errors.append(f"{rel}: {size/1024:.0f} KB exceeds the 400 KB budget")
            if not info["has_alpha"]:
                errors.append(f"{rel}: no alpha channel")
            if max(info["width"],info["height"])!=LONG_EDGE:
                errors.append(f"{rel}: long edge {max(info['width'],info['height'])} px, expected {LONG_EDGE}")
            boxes.append((asset.name,info["width"],info["height"]))
        if len(boxes)==2 and boxes[0][1:]!=boxes[1][1:]:
            errors.append(f"{category_id}: A/B canvases differ {boxes[0][1:]} vs {boxes[1][1:]} (the wiggle would jump)")
    return errors,warnings

def dependency_issues() -> list[str]:
    """Every direct dependency must appear in the public notices file."""
    import json
    notices=ROOT/"THIRD_PARTY_NOTICES.md"
    if not notices.is_file(): return ["Missing required file: THIRD_PARTY_NOTICES.md"]
    text=notices.read_text(encoding="utf-8")
    names=set()
    package=json.loads((ROOT/"frontend"/"package.json").read_text(encoding="utf-8"))
    names.update(package.get("dependencies",{})); names.update(package.get("devDependencies",{}))
    for rel in ("backend/requirements.txt","backend/requirements-stt.txt"):
        path=ROOT/rel
        if not path.is_file(): continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line=line.split("#",1)[0].strip()
            if line and not line.startswith("-"): names.add(line.split("==")[0].split(">=")[0].split("[")[0].strip())
    return [f"Dependency missing from THIRD_PARTY_NOTICES.md: {name} (run scripts/notices.py)" for name in sorted(names) if name and name not in text]

def run(strict: bool=False) -> list[str]:
    errors=[]
    for rel in REQUIRED:
        if not (ROOT/rel).is_file(): errors.append(f"Missing required file: {rel}")
    forbidden="TO"+"DO"
    for base in (ROOT/"frontend"/"src", ROOT/"backend"/"app"):
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".ts",".tsx",".py",".css"}: continue
            text=path.read_text(encoding="utf-8",errors="replace")
            if re.search(r"\{\{[A-Z][A-Z0-9_]*\}\}", text): errors.append(f"Unresolved template marker in {path.relative_to(ROOT)}")
            if forbidden in text: errors.append(f"Placeholder marker in {path.relative_to(ROOT)}")
            if strict and "dangerouslySetInnerHTML" in text: errors.append(f"Unsafe HTML sink in {path.relative_to(ROOT)}")
            if strict and path.suffix in {".ts",".tsx"} and re.search(r"\bconsole\.(?:log|debug|info)\(",text): errors.append(f"console logging in {path.relative_to(ROOT)}")
            if strict and re.search(r"localStorage\.(?:setItem|getItem)\([^\n]*(?:transcript|session.token|app.token)",text,re.I): errors.append(f"Potential sensitive localStorage use in {path.relative_to(ROOT)}")
    if strict:
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(x in path.parts or x.startswith(".venv") for x in ("node_modules",".git","dist",".pytest_cache","_scratch")): continue
            if path.name in {".env",".env.model"}:
                continue
            if path.suffix in {".py",".ts",".tsx",".json",".yaml",".yml",".sh",".md"}:
                text=path.read_text(encoding="utf-8",errors="replace")
                if re.search(r"(?:GEMINI_API_KEY|GROQ_API_KEY|SUPABASE_SERVICE_KEY|APP_TOKEN|BOT_API_KEY|BOT_WORKER_SECRET)\s*=\s*['\"]?(?!replace|dev-token|$)[A-Za-z0-9_\-/.]{24,}",text):
                    errors.append(f"Possible hard-coded credential in {path.relative_to(ROOT)}")
    return errors

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--strict",action="store_true");args=parser.parse_args()
    issues=run(args.strict)
    asset_errors,asset_warnings=check_category_assets()
    issues+=asset_errors
    coverage=dependency_issues()
    if args.strict: issues+=coverage
    else:
        for warning in coverage: print("WARN:",warning)
    for warning in asset_warnings: print("WARN:",warning)
    if issues:
        for issue in issues: print("FAIL:",issue)
        raise SystemExit(1)
    print("ActionMint repository checks passed"+(" (strict)" if args.strict else ""))
