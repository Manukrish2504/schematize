# Changelog

All notable changes to this project are documented here. Versions follow [Semantic Versioning](https://semver.org).

## 1.0.0

First release.

### Skill
- Six-step workflow: preflight, read the codebase, decide what to draw, pick icons, write and render, deliver.
- Grounding rule: every box and arrow traces to a file; inferred items are labelled and listed.
- Overview plus detailed view by default; large systems split by concern instead of shrinking.
- Layout guidance drawn from an end-to-end test on a 9-service serverless repository.

### Rendering
- `schematize_style.py` and `schematize_board.html`: one shared style module and board per output folder.
- Boundary boxes for cloud, account, region, VPC, subnets, cluster, security and external scopes, with
  vendor or account logos in the corner and optional pastel panels.
- Numbered `step()` arrows plus `sync`, `event`, `data` and `ops` edge types.
- Each run writes a PNG, a self-contained SVG and an interactive HTML board.

### Board
- An editable whiteboard of the generated diagram, in one offline HTML file.
- Move, resize, retitle, recolour or hide any component or boundary box; connectors re-route and a
  boundary box carries what is inside it.
- Add text, sticky notes, rectangles, ellipses, arrows and freehand drawings. Inline text editing,
  duplicate, delete, nudge, undo and redo.
- Select several things with a marquee or Shift-click, group them, and reorder layers, including behind
  the generated components.
- Connectors are editable: relabel, recolour, hide, or drag an end onto a different component.
- Icon picker: add components from the icons already in the diagram, or search the full 2,400+ icon
  library and the folder's fetched logos while the board server is running.
- Arrows you draw attach to the components and shapes they join and follow them.
- To front / To back also applies to generated components.
- Without the server: Save to folder writes edits straight into a picked folder (Chromium browsers), and
  the icon picker searches a built-in index, loading pictures from a public CDN.
- Unmatched edits after a regeneration can be attached to a component by hand or discarded.
- Edits follow components through renames: by `nodeid` when the source sets one, otherwise by label,
  then by icon and position.
- Edits save automatically into the diagram folder (`<name>.board.json`, `.board.png`, `.board.svg`)
  through a local server started by `--open`, and survive re-rendering.
- Animated dashed flow lines; step-by-step playback of the numbered path with captions; trace a
  component's connections.
- Light and dark themes, following the OS preference.
- Download as PNG, SVG or animated GIF, matching the current board and theme. The GIF encoder is built in.

### Tooling
- `icons.py search` over 2,400+ bundled icons; `icons.py fetch` for full-colour brand logos.
- Test suite (`tests/test_skill.py`) and GitHub Actions CI.
