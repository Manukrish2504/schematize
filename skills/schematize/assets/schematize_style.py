"""House style for schematize diagrams. Copy this file next to your diagram scripts; don't edit per diagram.

    from schematize_style import *
    with diagram("Checkout - overview", "architecture-overview"):
        with group("AWS Cloud", "cloud", icon="diagram-icons/aws.png"):
            ...
        users >> step(desc="Browser loads the app") >> cdn

Each run writes <filename>.png, a self-contained <filename>.svg and <filename>.html - an editable
board (move/resize/retitle anything, add text, notes, shapes, arrows and drawings; play the numbered
flow; dark mode; PNG/SVG/GIF download). Needs schematize_board.html alongside.

Add --open to launch the board from a small local server so that edits are saved into this folder as
<filename>.board.json (+ .board.png / .board.svg) and survive re-rendering.
"""
import base64
import html
import json
import mimetypes
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path

import diagrams
from diagrams import Cluster, Diagram, Edge, Node  # noqa: F401
from diagrams.custom import Custom  # noqa: F401

__all__ = ["diagram", "group", "step", "sync", "event", "data", "ops", "Custom", "Edge", "Node", "TINTS"]

FONT = "Helvetica"
GROUPS = {  # kind: (border, fill, border style)
    "cloud":    ("#232F3E", "#FFFFFF", "solid"),   # AWS Cloud / Azure / GCP outer box
    "account":  ("#C7255E", "#FFFFFF", "solid"),   # AWS account, Azure subscription, GCP project
    "region":   ("#00A4A6", "#FFFFFF", "dashed"),
    "vpc":      ("#8C4FFF", "#FFFFFF", "solid"),   # VPC / VNet
    "public":   ("#7AA116", "#F2F6E8", "solid"),   # public subnet
    "private":  ("#00A4A6", "#E6F6F7", "solid"),   # private subnet
    "cluster":  ("#326CE5", "#EEF3FD", "solid"),   # Kubernetes cluster / namespace
    "security": ("#DD344C", "#FFFFFF", "dashed"),  # security group / trust boundary
    "external": ("#7D8998", "#F7F8FA", "dashed"),  # third-party SaaS, anything you don't run
    "group":    ("#5A6B86", "#FFFFFF", "dashed"),  # generic logical grouping
    "panel":    ("#C9CED6", "#F1F3F5", "solid"),   # soft filled panel - pair with fill="yellow" etc.
}
TINTS = dict(yellow="#FFF6D6", green="#E9F5DC", blue="#E3EEFC", purple="#EEE7FB", red="#FCE6E6",
             orange="#FDEBD8", teal="#DDF3F2", grey="#F1F3F5")

_step = [0]


def _icon_path(icon):
    if isinstance(icon, str):
        return os.path.abspath(icon)
    # a diagrams node class: resolve its bundled PNG without creating a node
    return os.path.join(os.path.dirname(os.path.dirname(diagrams.__file__)), icon._icon_dir, icon._icon)


def _br(text):
    return html.escape(str(text)).replace("\n", "<br/>")


def group(label, kind="group", icon=None, fill=None):
    """Boundary box: `with group("prod account", "account", icon=OrganizationsAccount):`

    icon: diagrams node class or PNG path, drawn in the top-left corner (vendor logo, account/VPC
          marker, or the tech stack of what's inside).
    fill: TINTS name or hex colour, for a soft pastel panel.
    """
    color, bg, style = GROUPS[kind]
    text = _br(label)
    if icon:
        path = _icon_path(icon)
        if not os.path.isfile(path):
            sys.exit(f"group icon not found: {path} (run icons.py fetch, or pass a diagrams node class)")
        text = (f'<table border="0" cellborder="0" cellspacing="0"><tr>'
                f'<td fixedsize="true" width="30" height="30"><img src="{path}" scale="true"/></td>'
                f'<td align="left">&nbsp;{text}</td></tr></table>')
    return Cluster(f"<{text}>", graph_attr=dict(
        pencolor=color, fontcolor="#3D4756" if kind == "panel" else color, bgcolor=TINTS.get(fill, fill or bg), style=style, penwidth="2",
        labeljust="l", labelloc="t", fontsize="15", fontname=FONT, margin="22"))


def step(note="", desc="", color="#1B9E3E", **attrs):
    """Numbered arrow on the main path: `a >> step() >> b >> step("JWT", "API verifies the token") >> c`.

    note: short text under the number. desc: one sentence shown when this step plays in the HTML view.
    Numbers are assigned in call order. Connecting to a list gives every branch the same number.
    """
    _step[0] += 1
    n = _step[0]
    extra = f'<tr><td><font color="white" point-size="10"><b>{_br(note)}</b></font></td></tr>' if note else ""
    attrs.setdefault("class", f"step step-{n}")
    return Edge(color=color, penwidth="2.5", tooltip=desc or note or f"Step {n}", label=(
        f'<<table border="0" cellborder="0" cellpadding="3" bgcolor="{color}" style="rounded">'
        f'<tr><td><font color="white"><b> {n} </b></font></td></tr>{extra}</table>>'), **attrs)


def _edge(label, **attrs):
    if label:  # white plate keeps the text readable where it crosses a line
        attrs["label"] = (f'<<table border="0" cellpadding="2" bgcolor="white"><tr><td>'
                          f'<font point-size="11">{_br(label)}</font></td></tr></table>>')
    attrs.setdefault("penwidth", "1.6")
    return Edge(fontname=FONT, **attrs)


# Every helper takes extra Graphviz edge attributes, e.g. sync("auth", constraint="false", minlen="2").
def sync(label="", **attrs):   # plain synchronous call / dependency
    return _edge(label, color="#545B64", **attrs)


def event(label="", **attrs):  # async: queue, topic, webhook, stream, schedule
    return _edge(label, color="#C7255E", style="dashed", **attrs)


def data(label="", **attrs):   # reads/writes to a datastore
    return _edge(label, color="#3B48CC", **attrs)


def ops(label="", **attrs):    # deploy / manage / observe
    return _edge(label, color="#7D8998", style="dotted", **attrs)


@contextmanager
def diagram(title, filename, direction="LR", **graph_attr):
    """`with diagram("Title", "architecture-overview", direction="LR", nodesep="0.9"):`"""
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))  # outputs land next to the script
    _step[0] = 0
    attrs = dict(bgcolor="white", pad="0.4", nodesep="0.7", ranksep="1.1", dpi="144", fontname=FONT,
                 fontsize="20", labelloc="t", splines="spline", compound="true")
    attrs.update(graph_attr)
    with Diagram(title, filename=filename, direction=direction, outformat=["png", "svg"], show=False,
                 graph_attr=attrs, node_attr=dict(fontname=FONT, fontsize="12")):
        yield
    svg = Path(f"{filename}.svg")

    def inline(m):  # embed icons so the SVG works anywhere and leaks no local paths
        f = Path(m.group(2))
        if not f.is_file():
            return m.group(0)
        mime = mimetypes.guess_type(f.name)[0] or "image/png"
        return f'{m.group(1)}data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}"'

    text = re.sub(r'(xlink:href=")([^"]+)"', inline, svg.read_text())
    # Graphviz copies a box's HTML label (with its local icon path) into <title>; drop those
    text = re.sub(r"<title>[^<]*&lt;[^<]*</title>", "<title></title>", text)
    svg.write_text(text)
    body = text[text.index("<svg"):]
    # The board keeps what the user edits in <filename>.board.json; carry it across re-renders.
    saved = Path(f"{filename}.board.json")
    state = saved.read_text() if saved.is_file() else "null"
    template = (Path(__file__).resolve().parent / "schematize_board.html").read_text()
    board = Path(f"{filename}.html")
    # The icon picker works without the board server too: the index is embedded, pictures come from a CDN.
    library = Path(diagrams.__file__).resolve().parent.parent / "resources"
    icons = "\n".join(sorted(f.relative_to(library).with_suffix("").as_posix() for f in library.rglob("*.png")))
    try:
        from importlib.metadata import version
        cdn = f"https://cdn.jsdelivr.net/gh/mingrammer/diagrams@v{version('diagrams')}/resources/"
    except Exception:
        cdn = "https://cdn.jsdelivr.net/gh/mingrammer/diagrams@master/resources/"
    fill = dict(TITLE=html.escape(title), FILE=filename, STATE=state.replace("</", "<\\/"), SVG=body, ICONS=icons, CDN=cdn)
    board.write_text(re.sub(r"__(TITLE|FILE|STATE|SVG|ICONS|CDN)__", lambda m: fill[m.group(1)], template))
    print(f"wrote {filename}.png  {filename}.svg  {filename}.html")
    if "--open" in sys.argv:
        _launch(Path.cwd(), board.name)



# ---- board server: lets the board save edits into this folder ----------------------------------------
# `uv run <diagram>.py --open` starts it in the background on 127.0.0.1 and opens the board. It serves
# only this folder, accepts saves only from pages it served (per-run token), and exits by itself after
# 30 minutes without a request.
PORTS = range(4747, 4767)


def _probe(port):
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/__schematize", timeout=0.4) as r:
            return json.loads(r.read()).get("folder")
    except Exception:
        return None


def _launch(folder, page):
    import socket
    import subprocess
    import time
    import webbrowser

    folder = str(Path(folder).resolve())
    port = next((p for p in PORTS if _probe(p) == folder), None)  # already serving this folder?
    if port is None:
        for port in PORTS:
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    break
        else:
            sys.exit("no free port for the board server between 4747 and 4766")
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--serve", folder, str(port)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        for _ in range(50):
            if _probe(port) == folder:
                break
            time.sleep(0.1)
        else:
            sys.exit("the board server did not start")
    url = f"http://127.0.0.1:{port}/{page}"
    print(f"board: {url}  (edits are saved into {folder})")
    webbrowser.open(url)


def _serve(folder, port, idle=1800):
    import secrets
    import threading
    import time
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    import urllib.parse

    root, token, seen = Path(folder).resolve(), secrets.token_urlsafe(18), [time.time()]
    library = Path(diagrams.__file__).resolve().parent.parent / "resources"
    index = [{"p": f.relative_to(library).as_posix(), "name": f.stem.replace("-", " "), "k": f.relative_to(library).as_posix().lower().replace("-", "")}
             for f in sorted(library.rglob("*.png"))]
    index += [{"p": f"local/{f.name}", "name": f.stem.replace("-", " "), "k": f"local{f.stem.lower()}"}
              for f in sorted((root / "diagram-icons").glob("*.png"))]

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(root), **k)

        def log_message(self, *a):
            pass

        def list_directory(self, path):
            self.send_error(404)

        def _local(self):  # refuse requests that arrive under another host name (DNS rebinding)
            seen[0] = time.time()
            host = (self.headers.get("Host") or "").split(":")[0]
            if host in ("127.0.0.1", "localhost"):
                return True
            self.send_error(403)
            return False

        def _send(self, body, ctype):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self._local():
                return
            path = self.path.split("?")[0].lstrip("/")
            if path == "__schematize":
                return self._send(json.dumps({"folder": str(root)}).encode(), "application/json")
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if path == "__icons":  # search the bundled icon library and this folder's fetched logos
                words = re.findall(r"[a-z0-9]+", (query.get("q") or [""])[0].lower())
                hits = [i for i in index if all(w in i["k"] for w in words)] if words else []
                hits.sort(key=lambda i: (len(i["name"]), i["p"]))
                return self._send(json.dumps([{"name": i["name"], "p": i["p"]} for i in hits[:80]]).encode(), "application/json")
            if path == "__icon":
                rel = (query.get("p") or [""])[0]
                base = root / "diagram-icons" if rel.startswith("local/") else library
                target = (base / rel.removeprefix("local/")).resolve()
                if target.suffix != ".png" or not target.is_file() or base.resolve() not in target.parents:
                    return self.send_error(404)
                return self._send(target.read_bytes(), "image/png")
            page = root / path
            if re.fullmatch(r"[\w.-]+\.html", path) and page.is_file():
                hook = f"<script>window.SCHEMATIZE={json.dumps({'token': token})}</script></head>"
                return self._send(page.read_text().replace("</head>", hook, 1).encode(), "text/html; charset=utf-8")
            super().do_GET()

        def do_POST(self):
            if not self._local():
                return
            size = int(self.headers.get("Content-Length") or 0)
            if self.path != "/__save" or self.headers.get("X-Schematize") != token or not 0 < size < 80_000_000:
                return self.send_error(403)
            data = json.loads(self.rfile.read(size))
            name = str(data.get("name", ""))
            page = root / f"{name}.html"
            if not re.fullmatch(r"[\w.-]+", name) or not page.is_file() or not isinstance(data.get("state"), dict):
                return self.send_error(400)
            state = json.dumps(data["state"], indent=1)
            (root / f"{name}.board.json").write_text(state + "\n")
            if isinstance(data.get("svg"), str):
                (root / f"{name}.board.svg").write_text(data["svg"])
            if isinstance(data.get("png"), str):
                (root / f"{name}.board.png").write_bytes(base64.b64decode(data["png"]))
            # keep the standalone HTML current too, so it opens with the edits even without the server
            embedded = json.dumps(data["state"]).replace("</", "<\\/")
            text = re.sub(r'(<script id="board-state" type="application/json">).*?(</script>)',
                          lambda m: m.group(1) + embedded + m.group(2), page.read_text(), count=1, flags=re.S)
            page.write_text(text)
            self._send(b"{}", "application/json")

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)

    def reaper():
        while time.time() - seen[0] < idle:
            time.sleep(15)
        server.shutdown()

    threading.Thread(target=reaper, daemon=True).start()
    server.serve_forever()


if __name__ == "__main__" and sys.argv[1:2] == ["--serve"]:
    _serve(sys.argv[2], int(sys.argv[3]))
