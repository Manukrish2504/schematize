# /// script
# requires-python = ">=3.9,<3.15"
# dependencies = ["diagrams>=0.24", "resvg-py"]
# ///
"""Icon helper for the schematize skill.

  uv run icons.py search lambda "api gateway" postgres   # find bundled icons -> import lines
  uv run icons.py fetch aws vercel supabase [-o DIR]      # download colour brand logos as PNG
"""
import importlib
import json
import pkgutil
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def search(terms, limit=12):
    import diagrams

    index = []  # (haystack, import line)
    for prov in pkgutil.iter_modules(diagrams.__path__):
        if not prov.ispkg:
            continue
        pkg = importlib.import_module(f"diagrams.{prov.name}")
        for mod in pkgutil.iter_modules(pkg.__path__):
            name = f"diagrams.{prov.name}.{mod.name}"
            m = importlib.import_module(name)
            for cls, obj in vars(m).items():
                if isinstance(obj, type) and getattr(obj, "_icon", None):
                    index.append((norm(f"{prov.name}{mod.name}{cls}{obj._icon}"), norm(cls), f"from {name} import {cls}"))
    for term in terms:
        words = [norm(w) for w in term.split()]
        hits = [(cls != norm(term), len(cls), line) for hay, cls, line in index if all(w in hay for w in words)]
        print(f"# {term}: {len(hits)} match(es)")
        for *_, line in sorted(hits)[:limit]:  # exact class-name match first, then shortest
            print(line)
        if not hits:
            print("#   none bundled -> if it is a brand, try `icons.py fetch <brand>`; otherwise use a generic icon")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "schematize"})
    return urllib.request.urlopen(req, timeout=20).read().decode()


def fetch(slugs, out):
    import resvg_py

    out.mkdir(parents=True, exist_ok=True)
    ok = True
    for raw in slugs:
        slug = re.sub(r"[^a-z0-9-]", "", raw.lower())
        # full-colour marks (gilbarbara/logos, CC0) first, then single-colour simpleicons (CC0)
        urls = [f"https://api.iconify.design/logos/{slug}-icon.svg", f"https://api.iconify.design/logos/{slug}.svg",
                f"https://cdn.simpleicons.org/{slug.replace('-', '')}"]
        svg = None
        for url in urls:
            try:
                svg = _get(url)
                break
            except urllib.error.HTTPError:
                continue
        if svg is None:
            hint = ""
            try:
                hint = ", ".join(i.split(":")[1] for i in json.loads(
                    _get(f"https://api.iconify.design/search?query={slug}&prefix=logos&limit=8"))["icons"])
            except Exception:
                pass
            print(f"{slug}: not found" + (f" - did you mean: {hint}" if hint else " - use a generic icon"), file=sys.stderr)
            ok = False
            continue
        dest = out / f"{slug}.png"
        dest.write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=svg, width=256)))
        print(dest)
    return ok


def main(argv):
    if len(argv) < 2 or argv[0] not in ("search", "fetch"):
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    if cmd == "search":
        search(args)
    else:
        out = Path("diagram-icons")
        if "-o" in args:
            i = args.index("-o")
            out = Path(args[i + 1])
            args = args[:i] + args[i + 2:]
        sys.exit(0 if fetch(args, out) else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
