from __future__ import annotations
import argparse, sys
import httpx

def main() -> int:
    parser=argparse.ArgumentParser(description="Check a deployed ActionMint API health endpoint")
    parser.add_argument("url",help="API origin, e.g. https://api.example.tech")
    args=parser.parse_args(); url=args.url.rstrip("/")+"/health"
    try:
        r=httpx.get(url,timeout=12);r.raise_for_status();data=r.json()
        healthy=any(p.get("ok") for p in data.get("providers",[]))
        if data.get("status")!="ok" or not healthy:
            print("Unhealthy:",data.get("status"),"no provider is ready");return 1
        print("Healthy:",url,"providers:",", ".join(p["name"] for p in data["providers"] if p.get("ok")));return 0
    except Exception as exc:
        print(f"Health check failed: {type(exc).__name__}: {exc}",file=sys.stderr);return 1
if __name__=="__main__": raise SystemExit(main())
