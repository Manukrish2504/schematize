---
name: schematize
description: Reads a codebase end to end and draws its architecture as a presentation-grade system diagram with real vendor icons (AWS, Azure, GCP, Kubernetes, 100+ SaaS/on-prem logos), nested account/VPC/cluster boundaries and numbered request flows - the kind of diagram teams draw by hand in Miro, Lucidchart or draw.io. Produces PNG + SVG plus re-renderable Python source. Use when the user asks for an architecture diagram, system design diagram, infra/cloud diagram, "draw/visualize/map this codebase", an AWS/Azure/GCP diagram, or says "schematize". Not for sequence diagrams, ER diagrams or quick inline Mermaid sketches.
---

# Schematize

Turn a codebase into the architecture diagram an engineer would present in a design review:
official cloud icons, labelled boundary boxes, coloured and numbered flows.

Rendering is done by the [`diagrams`](https://diagrams.mingrammer.com) Python library (2,400+ bundled
vendor icons) on top of Graphviz. You write one small Python file per diagram; each run produces a PNG,
a self-contained SVG, and an HTML **board** - an editable whiteboard of the diagram. On the board the
user can move, resize, retitle, recolour or hide anything you drew; relabel a connector or drag its end
onto a different component; add components from the icon library, text, sticky notes, shapes, arrows
and freehand drawings; select several things, group them and reorder layers; undo and redo; play the
numbered path step by step; switch light/dark; and download PNG, SVG or an animated GIF. Their edits are saved automatically into the
diagram folder and survive re-rendering.

`SKILL_DIR` in the commands below is a placeholder: substitute the absolute path of the directory
containing this file.

## 0. Preflight

```bash
dot -V          # Graphviz. Missing -> brew install graphviz | apt-get install graphviz | choco install graphviz
uv --version    # Preferred runner; scripts carry their own dependencies (PEP 723)
```

The first `uv run` of each script installs its dependencies into a cached environment (a few seconds).

No `uv`? Use `python3 -m pip install diagrams resvg-py` and run the same scripts with `python3`.
If Graphviz cannot be installed, stop and tell the user - do not fall back to ASCII or Mermaid silently.

## 1. Read the codebase - all of it that describes the system

The diagram is only as good as the inventory. Read before drawing; do not draw from the README alone.
For a large repo, fan out read-only subagents by area (infra / services / data / CI) and merge their findings.

Read, in this order:

1. **Stated intent** - `README*`, `docs/`, `ARCHITECTURE*`, ADRs, `CLAUDE.md` / `AGENTS.md`, any agent memory
   directory for this project. Look at existing diagram images too (Read tool) - they give you the team's
   own vocabulary and grouping, though the code wins where they disagree.
2. **Infrastructure as code** - the ground truth for cloud resources and boundaries:
   Terraform/OpenTofu (`*.tf`, modules, `*.tfvars`), CloudFormation/SAM, CDK, Pulumi, Bicep/ARM,
   `serverless.yml`, Kubernetes manifests, Helm charts, Kustomize overlays, `docker-compose*.yml`,
   `Dockerfile`s, `fly.toml`, `vercel.json`/`vercel.ts`, `netlify.toml`, `render.yaml`, `wrangler.toml`.
3. **Deployable units** - every service/app/worker/function/cron: monorepo workspaces, `apps/`, `services/`,
   `cmd/`, entrypoints, `Procfile`. One box per thing that is deployed or scaled separately.
4. **Connections** - what each unit talks to: HTTP/gRPC clients, SDK imports (`boto3`, `@aws-sdk/*`,
   `stripe`, `openai`, `@supabase/*`, ...), ORM/driver config, queue/topic producers and consumers,
   webhooks, env var names in `.env.example` / config schemas / secrets manifests (names only - never
   print or copy secret values).
5. **Edges of the system** - who calls in (web, mobile, partners, cron) and what is called out to
   (auth, payments, email, LLM APIs, analytics, observability).
6. **Delivery** - CI/CD workflows, registries, deploy targets, environments/accounts.

Build an inventory as you go (keep it in context, or write it into the companion markdown in step 5):

| id | component | kind | boundary (account/VPC/cluster/...) | talks to (protocol, sync/async) | evidence `file:line` |

**Grounding rule: every box and every arrow must trace to a file you read.** Nothing is drawn because
"systems like this usually have one". If something is strongly implied but not declared (e.g. a database
URL env var with no IaC), draw it and mark the label `(inferred)`. If the repo has no infrastructure
definition at all, say so and draw the logical architecture (services, stores, external APIs) instead
of inventing a cloud layout.

## 2. Decide what to draw

Default deliverable is an **overview** plus a **detailed** view, unless the user asked for only one:

- **Overview** (`architecture-overview`) - the one-slide version. 6-12 nodes. Collapse replicas,
  per-environment copies and plumbing (IAM roles, log groups, security groups, route tables) into their
  parent. One numbered path: the primary user request, start to finish.
- **Detailed** (`architecture-detailed`) - what an on-call engineer needs. Every deployable unit, data
  store, queue, external dependency and network boundary; accounts/VPCs/subnets/namespaces as nested
  boxes; sync vs async vs data edges distinguished.

**If the detailed view would exceed ~25 nodes, replace it with several focused diagrams** - do not shrink
it to fit. Name them after what this system is actually made of: `architecture-requests` (synchronous
path), `architecture-events` (async/bus), `architecture-network`, `architecture-data`, `architecture-cicd`,
or one per bounded context / account. A rendered PNG wider than ~3500 px is the same signal: split.
Number the main path in any diagram that has one linear path; leave hub-and-spoke diagrams (event bus,
shared database) unnumbered. Organisation structures (AWS Organizations, OUs, accounts, management
groups, subscriptions) get their own `direction="TB"` tree.

Simplify without lying:

- Many components doing the same thing to one target (13 Lambdas -> one DLQ, every service -> the log
  sink): draw one edge from a representative or from the enclosing box's first node and say so in the
  label (`"all handlers"`) and in the README.
- Environments that are copies (dev/staging/prod as stack prefixes or tfvars, not separate accounts):
  draw once, label the boundary `{env}` and list the environments in the README. Separate accounts or
  clusters per environment get separate boxes in the detailed view.

## 3. Pick icons

Never guess an import path - look it up:

```bash
uv run SKILL_DIR/scripts/icons.py search lambda "api gateway" "azure sql" kafka stripe
# -> from diagrams.aws.compute import Lambda ...
```

Resolution order for each component:

1. **Bundled official icon** from `search` (AWS, Azure, GCP, K8s, OCI, Alibaba, DigitalOcean, IBM, Elastic,
   Firebase, on-prem OSS, SaaS, programming languages/frameworks).
2. **Fetched brand logo** for anything else, in full colour (Vercel, Supabase, Clerk, OpenAI, ...):
   ```bash
   uv run SKILL_DIR/scripts/icons.py fetch aws vercel supabase -o <output folder>/diagram-icons
   ```
   Logos fetched into `diagram-icons/` also show up in the board's icon picker.
   then `Custom("Supabase", "diagram-icons/supabase.png")` - paths are relative to the diagram script.
   Slugs are lower-case brand names; a miss prints "did you mean" suggestions. The command exits 1 if
   any slug failed, but the ones it printed a path for were written. Commit `diagram-icons/`.
3. **Generic icon** when there is no logo (`diagrams.generic.*`, `diagrams.onprem.compute.Server`,
   `diagrams.programming.language.*` for an in-house service written in that language).

**Always fetch the platform logos the diagram needs for its boundary boxes** - `aws`, `microsoft-azure`,
`google-cloud`, `kubernetes`, `vercel`, ... The cloud's own logo is not in the bundled set, and a cloud
box without its logo in the corner does not read as a cloud diagram.

Use the icon of the thing actually deployed: a Node service on ECS Fargate is a `Fargate` icon labelled
with the service name, not a Node.js logo. Label = the name the team uses, plus the technology on a
second line if useful (`"orders-api\n(FastAPI)"`).

## 4. Write and render

Into the output folder (default `docs/architecture/`):

1. Copy `SKILL_DIR/assets/schematize_style.py` **and** `SKILL_DIR/assets/schematize_board.html` there
   once, unmodified. They are the house style and the board, shared by every diagram script in the folder.
2. Write one script per diagram, modelled on `SKILL_DIR/assets/example.py` (read it - it is 40 lines):
   the PEP 723 header, `from schematize_style import *`, the icon imports, one `with diagram(...)` block.

```bash
uv run docs/architecture/architecture-overview.py
# wrote architecture-overview.png  architecture-overview.svg  architecture-overview.html
```

| helper | draws | use for |
|---|---|---|
| `diagram(title, filename, direction="LR", **graph_attrs)` | the canvas | one per script |
| `group(label, kind, icon=None, fill=None)` | boundary box with optional corner logo | kinds: `cloud`, `account`, `region`, `vpc`, `public`, `private`, `cluster`, `security`, `external`, `group`, `panel` |
| `step(note="", desc="")` | thick green arrow, auto-numbered badge | the primary path, in order |
| `sync(label)` | grey solid | other synchronous calls |
| `event(label)` | magenta dashed | queues, topics, webhooks, streams, schedules |
| `data(label)` | blue solid | reads/writes to a datastore |
| `ops(label)` | grey dotted | deploy, manage, monitor |

- **Corner logos:** `group("AWS Cloud", "cloud", icon="diagram-icons/aws.png")`. `icon` also takes a bundled
  class: `icon=OrganizationsAccount` for accounts, `VPC`, `PublicSubnet`/`PrivateSubnet`, `Namespace`,
  Azure `Subscriptions`/`ResourceGroups`, GCP `Project`. Put a logo on every cloud/account/VPC/cluster box.
  It can also show the stack inside a box (`icon="diagram-icons/dotnet.png"`).
- **Soft panels:** `group("Storage accounts", "panel", fill="yellow")` gives the pastel filled-panel look
  (`yellow green blue purple red orange teal grey`, or any hex). Use tints to separate tiers or teams
  inside a cloud box; keep real security/network boundaries as the outlined kinds.
- **Step text:** `step("HTTPS", "The SPA calls the orders API with the user's JWT")` - `note` prints under
  the number, `desc` is the sentence shown when that step plays in the HTML view. Give every step a `desc`.
  Numbers follow call order. Connecting to a list (`a >> step() >> [b, c]`) gives every branch the same
  number - right for parallel calls; for sequential branches write one statement each.
- **Both directions:** `a >> edge >> b` draws a->b. `a << edge << b` draws b->a *while keeping `a` ranked
  first* - use it when a later-ranked node sends back to an earlier one (publishers -> a bus on the left).
- **Stable ids:** give every node a `nodeid` - a short, permanent slug for the component:
  `Lambda("orders-api\n(FastAPI)", nodeid="orders-api")`. The board ties the user's edits to it, so a
  later relabel in this file keeps their moved positions, renames and re-pointed connectors. Use
  lower-case letters, digits and hyphens; never reuse or change an id once a `<name>.board.json` exists.
  (Without ids the board falls back to matching by label, then by icon and position.)
- **Extra attributes:** every edge helper accepts Graphviz edge attributes: `sync("auth", constraint="false")`,
  `event("retry", minlen="2")`. Line breaks in any label are `\n`.

### Layout rules (Graphviz is automatic - you steer it, you don't place things)

- `direction="LR"` for request/data flows, `"TB"` for hierarchies. If the PNG comes out more than about
  twice as tall as wide (or the reverse) and the page it is going on is the other shape, flip it.
- Declare nodes in reading order and write the main path's edges first; Graphviz ranks by edge order.
- Fan-out: connect to a list (`api >> sync() >> [svc_a, svc_b, svc_c]`) instead of three statements.
- **A single edge that runs against the flow** (a callback, a deploy arrow, a cache check) drags nodes
  out of place: give that one edge `constraint="false"`. Do not put `constraint="false"` on several
  edges into the same node or between neighbouring boxes - they tangle; reduce them to one
  representative edge instead.
- **A hub (event bus, shared DB, gateway) that sits outside the boxes of the things it connects** makes
  Graphviz put it at one end and draw half the arrows backwards. Either put the hub in its own box
  between producer and consumer groups, split producers and consumers into separate boxes, or drop the
  enclosing box around them.
- Keep `splines="spline"`. `"ortho"` gives right-angle lines but Graphviz then detaches edge labels and
  number badges from their lines; only pass `splines="ortho"` to a diagram with no edge labels at all
  (organisation trees are a good fit).
- Graphviz places a badge or label *beside* its line, not on it, and may drop it on a box title. When
  that happens, shorten the label, add `minlen="2"` to that edge, or move the label to the other edge of
  a two-hop path.
- Boundary boxes nest at most 3-4 deep. An empty box is noise; a one-node box is fine only when the
  boundary itself is the point (a third-party service, a separate account).
- Short labels: two lines max, about 18 characters per line.
- Overlapping or touching things -> raise `nodesep`/`ranksep` (`diagram(..., nodesep="1.0")`). Spacing
  does not fix crossing lines - fewer edges, a different direction, or a split does.

### Look at it, then fix it

Rendering without looking is not done. Open the PNG with the Read tool and check, in this order:

1. Is every inventory item present, and is there nothing that is not in the inventory?
2. Does every cloud/account/cluster box carry its logo?
3. Does the numbered path read 1..N in the direction of the layout without doubling back?
4. Are any labels sitting on lines, box borders or titles; any arrows passing behind icons; any line
   looping the long way round?
5. Would a new engineer understand the system in 30 seconds from the overview?

Fix and re-render. Two or three passes per diagram is normal; stop when what is left is cosmetic, and
list anything you could not fix in the README.

## 5. Deliver

In the output folder:

- per diagram: `<name>.png` (slides, docs, Miro), `<name>.svg` (scalable, icons embedded),
  `<name>.html` (the interactive board), `<name>.py` (source of truth)
- `schematize_style.py`, `schematize_board.html`, and `diagram-icons/` if any logos were fetched
- later, written by the board when the user edits: `<name>.board.json` (their edits), `<name>.board.png`
  and `<name>.board.svg` (the diagram as edited). Never delete or overwrite these.
- `README.md` - embeds the PNGs and links the HTML views; for each diagram: a one-paragraph summary, the
  numbered steps explained, a legend for the arrow colours, the inventory table with evidence paths, and
  an **Assumptions & gaps** list (everything marked inferred, everything you could not determine).

**Then launch the board.** Once the diagrams are final, open the overview in the user's browser:

```bash
uv run <output folder>/architecture-overview.py --open
# board: http://127.0.0.1:4747/architecture-overview.html  (edits are saved into <output folder>)
```

`--open` re-renders, starts a small background server bound to 127.0.0.1 that serves only the output
folder, opens the board, and returns immediately. The server is what lets the board save into the
folder; it stops by itself after 30 minutes without use. Skip `--open` only in a headless/CI/remote
session, and say so. Don't pass it during the render-and-fix passes - one launch, at the end.

Tell the user:

- where the files are, and what was inferred rather than found;
- that the board is editable: double-click any text to change it, drag to move, drag a corner to
  resize, drag a box around several things or Shift-click to select many, select a connector to relabel
  it or drag its end to another component, and use the left toolbar to add icons, text, notes, shapes,
  arrows and drawings (Cmd/Ctrl+Z undoes);
- that edits save automatically into the folder as `<name>.board.json`, with the edited picture in
  `<name>.board.png` / `.board.svg`, while the board was opened with `--open`. Opened as a plain file,
  a Chromium browser offers "Save to folder" in the top-left corner to do the same without the server;
  other browsers keep edits in the browser and say so;
- that `uv run <output folder>/<name>.py` regenerates the diagram after a code change and keeps their
  board edits, which are matched to components by label.

**When you regenerate a diagram that already has a `<name>.board.json`:** keep every existing `nodeid`
exactly as it is, and add ids to nodes that lack them before changing their labels. If a saved edit no longer
matches a component the board shows an "unmatched edits" button where the user can attach it to the
right component or discard it - tell them when you have removed or re-identified components. If the user asks
you to change something they could change on the board (a title, a colour, a position), prefer editing
the `.py` so the change is in the source of truth. Do not commit unless asked.
