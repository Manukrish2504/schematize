# /// script
# requires-python = ">=3.9,<3.15"
# dependencies = ["diagrams>=0.24", "pillow"]
# ///
"""End-to-end checks for the schematize skill. Run:  uv run tests/test_skill.py

Needs Graphviz (`dot`) and Node.js on PATH. No network: the cloud logo is a generated placeholder.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "schematize"


def run(*cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"{' '.join(map(str, cmd))}\n{r.stdout}\n{r.stderr}"
    return r.stdout


def test_frontmatter():
    text = (SKILL / "SKILL.md").read_text()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md must start with YAML frontmatter"
    fields = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
    assert fields["name"].strip() == "schematize"
    assert 50 < len(fields["description"]) <= 1024, "description must be present and within the 1024-char limit"
    for ref in re.findall(r"SKILL_DIR/([\w/.]+)", text):
        assert (SKILL / ref).exists(), f"SKILL.md references a missing file: {ref}"


def test_manifests():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert plugin["name"] == "schematize" and market["plugins"][0]["name"] == "schematize"
    assert f"## {plugin['version']}" in (ROOT / "CHANGELOG.md").read_text(), "CHANGELOG has no entry for the plugin version"


def test_icon_search():
    out = run(sys.executable, SKILL / "scripts" / "icons.py", "search", "lambda", "definitely-not-an-icon")
    assert "from diagrams.aws.compute import Lambda" in out
    assert "# definitely-not-an-icon: 0 match(es)" in out


def render_example(tmp):
    shutil.copy(SKILL / "assets" / "example.py", tmp)
    shutil.copy(SKILL / "assets" / "schematize_style.py", tmp)
    shutil.copy(SKILL / "assets" / "schematize_board.html", tmp)
    (tmp / "diagram-icons").mkdir()
    Image.new("RGBA", (64, 40), "#FF9900").save(tmp / "diagram-icons" / "aws.png")
    out = run(sys.executable, tmp / "example.py", cwd=tmp)
    assert "wrote architecture-overview.png" in out
    return tmp


def test_render(tmp):
    png, svg, board = (tmp / f"architecture-overview.{e}" for e in ("png", "svg", "html"))
    with Image.open(png) as im:
        assert im.width > 1000 and im.height > 400
    s = svg.read_text()
    assert 'href="/' not in s and str(tmp) not in s, "SVG must embed icons, not reference local paths"
    assert s.count("data:image/png;base64,") >= 9
    for n in (1, 2, 3, 4):
        assert f"step&#45;{n}" in s or f"step-{n}" in s, f"step {n} edge is missing its class"
    assert 'xlink:title="Browser requests the web app"' in s, "step descriptions must reach the SVG"
    for nodeid in ("orders-api", "orders-table", "github-actions"):
        assert f"<title>{nodeid.replace('-', '&#45;')}</title>" in s, f"nodeid {nodeid} must reach the SVG so board edits can follow it"
    h = board.read_text()
    assert not re.search(r"__(SVG|TITLE|FILE|STATE|ICONS|CDN)__", h), "unfilled placeholder in board"
    index = re.search(r'<script id="icon-index" type="text/plain" data-cdn="(https://[^"]+/)">(.*?)</script>', h, re.S)
    assert index and "aws/compute/lambda" in index.group(2).split("\n"), "icon index must be embedded for the offline picker"
    assert str(tmp) not in h, "board must not leak local paths"
    assert not re.search(r"""(src|href)=["']https?://""", h), "board must be self-contained"
    return h


def test_state_survives_rerender(tmp):
    """Edits live in <name>.board.json; a re-render must carry them into the new board."""
    state = {"v": 1, "t": 1, "nodes": {"orders-table": {"dx": 5, "text": "x</script>y"}}, "groups": {}, "items": []}
    (tmp / "architecture-overview.board.json").write_text(json.dumps(state))
    run(sys.executable, tmp / "example.py", cwd=tmp)
    h = (tmp / "architecture-overview.html").read_text()
    m = re.search(r'<script id="board-state" type="application/json">(.*?)</script>', h, re.S)
    assert m and json.loads(m.group(1)) == state, "saved board state was not embedded intact"
    (tmp / "architecture-overview.board.json").unlink()
    run(sys.executable, tmp / "example.py", cwd=tmp)


def test_save_server(tmp):
    """The board server saves edits into the folder, and only for pages it served."""
    import socket
    import time
    import urllib.error
    import urllib.request

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen([sys.executable, tmp / "schematize_style.py", "--serve", tmp, str(port)])
    base = f"http://127.0.0.1:{port}"

    def call(path, body=None, headers=None):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, ""

    try:
        for _ in range(50):
            try:
                if call("/__schematize")[0] == 200:
                    break
            except OSError:
                time.sleep(0.1)
        status, page = call("/architecture-overview.html")
        token = re.search(r'window\.SCHEMATIZE=\{"token": "([^"]+)"\}', page)
        assert status == 200 and token, "served board must carry a save token"
        state = {"v": 1, "t": 2, "nodes": {}, "groups": {}, "items": [{"id": "a", "type": "text", "x": 1, "y": 2, "text": "hi </script>"}]}
        body = {"name": "architecture-overview", "state": state, "svg": "<svg/>", "png": "iVBORw0KGgo="}
        assert call("/__save", body)[0] == 403, "save without a token must be refused"
        assert call("/__save", body, {"X-Schematize": "wrong"})[0] == 403
        assert call("/__save", {**body, "name": "../evil"}, {"X-Schematize": token.group(1)})[0] == 400
        assert call("/__save", {**body, "name": "missing"}, {"X-Schematize": token.group(1)})[0] == 400
        assert call("/", None)[0] == 404, "directory listing must be off"
        found = json.loads(call("/__icons?q=aws+lambda")[1])
        assert any(i["p"] == "aws/compute/lambda.png" for i in found), "icon search must find bundled icons"
        assert any(i["p"] == "local/aws.png" for i in json.loads(call("/__icons?q=local")[1])), "icon search must list fetched logos"
        assert call("/__icon?p=aws/compute/lambda.png")[0] == 200
        assert call("/__icon?p=../../../../etc/passwd")[0] == 404 and call("/__icon?p=local/../example.py")[0] == 404
        assert call("/__save", body, {"X-Schematize": token.group(1)})[0] == 200
        assert json.loads((tmp / "architecture-overview.board.json").read_text()) == state
        assert (tmp / "architecture-overview.board.svg").read_text() == "<svg/>"
        assert (tmp / "architecture-overview.board.png").read_bytes().startswith(b"\x89PNG")
        h = (tmp / "architecture-overview.html").read_text()
        m = re.search(r'<script id="board-state" type="application/json">(.*?)</script>', h, re.S)
        assert json.loads(m.group(1)) == state, "standalone HTML must be updated with the saved state"
        assert not (tmp.parent / "evil.board.json").exists()
    finally:
        proc.terminate()
        proc.wait(5)
        for f in tmp.glob("*.board.*"):
            f.unlink()


def test_board_script(h, tmp):
    js = h[h.rindex("<script>") + 8:h.rindex("</script>")]
    (tmp / "board.js").write_text(js)
    run("node", "--check", tmp / "board.js")
    for control in ("prev", "play", "next", "all", "anim", "reset", "theme", "dl", "zin", "zout", "fit", "undo", "redo", "props", "status"):
        assert f'id="{control}"' in h, f"board is missing #{control}"
    for tool in ("select", "hand", "text", "note", "rect", "ellipse", "arrow", "icon", "pen"):
        assert f'data-tool="{tool}"' in h, f"board is missing the {tool} tool"
    for kind in ("png", "svg", "gif"):
        assert f'data-dl="{kind}"' in h and re.search(rf"async {kind}\(", js), f"no {kind} download"
    return js


def test_gif_encoder(js, tmp):
    """Run the board's encoder under node on synthetic frames, then decode with Pillow and compare pixels."""
    enc = js[js.index("// <gif-encoder>"):js.index("// </gif-encoder>")]
    w, h = 97, 61  # odd sizes; enough pixels to grow the LZW code width, noise frame forces table resets
    (tmp / "enc.js").write_text(enc + f"""
const w = {w}, h = {h}, mk = f => {{ const d = new Uint8ClampedArray(w * h * 4);
  for (let i = 0; i < w * h; i++) {{ const x = i % w, y = i / w | 0; let r, g, b;
    if (f === 0) {{ r = x * 255 / w; g = y * 255 / h; b = 128; }}                     // gradient
    else if (f === 1) {{ r = g = b = ((x >> 3) + (y >> 3)) % 2 ? 255 : 0; }}           // checkerboard
    else {{ const v = (i * 2654435761 >>> 0); r = v & 255; g = v >> 8 & 255; b = v >> 16 & 255; }}  // noise
    d.set([r, g, b, 255], i * 4); }}
  return d; }};
const rgba = [0, 1, 2].map(mk), q = quantizer(rgba), idx = rgba.map(d => q.index(d));
const gif = gifEncode(w, h, q.palette, [idx[0], idx[1], idx[2], idx[0]], [25, 25, 40, 25]);
require('fs').writeFileSync('out.gif', gif);
require('fs').writeFileSync('expect.json', JSON.stringify({{ palette: [...q.palette], frames: idx.map(a => [...a]) }}));
""")
    run("node", tmp / "enc.js", cwd=tmp)
    expect = json.loads((tmp / "expect.json").read_text())
    pal = expect["palette"]
    with Image.open(tmp / "out.gif") as im:
        assert im.format == "GIF" and im.size == (w, h) and im.n_frames == 4
        assert im.info.get("loop") == 0, "GIF must loop forever"
        for i, src in enumerate([0, 1, 2, 0]):
            im.seek(i)
            assert im.info["duration"] == (400 if i == 2 else 250)
            want = bytes(c for j in expect["frames"][src] for c in pal[j * 3:j * 3 + 3])
            assert im.convert("RGB").tobytes() == want, f"frame {i} decodes to different pixels"


if __name__ == "__main__":
    for tool in ("dot", "node"):
        assert shutil.which(tool), f"{tool} is required to run the tests"
    test_frontmatter(); print("ok  SKILL.md frontmatter and file references")
    test_manifests(); print("ok  plugin manifests and changelog")
    test_icon_search(); print("ok  icon search")
    with tempfile.TemporaryDirectory() as d:
        tmp = render_example(Path(d).resolve())
        html = test_render(tmp); print("ok  example renders PNG + self-contained SVG + board")
        js = test_board_script(html, tmp); print("ok  board script parses, controls and downloads present")
        test_gif_encoder(js, tmp); print("ok  GIF encoder round-trips through Pillow")
        test_state_survives_rerender(tmp); print("ok  board edits survive a re-render")
        test_save_server(tmp); print("ok  board server saves into the folder and refuses untrusted writes")
    print("all checks passed")
