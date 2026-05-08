<p align="center">
  <img src="https://raw.githubusercontent.com/pathsim/pathsim-docs/master/static/pathsim_logo.png" width="300" alt="PathSim Logo" />
</p>

------------

# PathSim Docs - Unified Documentation Site

A unified documentation site for the PathSim ecosystem, featuring API references, interactive examples, and versioned documentation for PathSim, PathSim-Chem, and PathSim-Vehicle. Built with SvelteKit and hosted at [docs.pathsim.org](https://docs.pathsim.org).

## Tech Stack

- [SvelteKit 2](https://kit.svelte.dev/) with Svelte 5 runes
- [Griffe](https://mkdocstrings.github.io/griffe/) for Python API extraction
- [Pyodide](https://pyodide.org/) for interactive notebook execution
- [CodeMirror 6](https://codemirror.net/) for code highlighting
- [KaTeX](https://katex.org/) for math rendering
- [Marked](https://marked.js.org/) for Markdown processing
- [Transformers.js](https://huggingface.co/docs/transformers.js/) for semantic search (e5-small-v2)

## Getting Started

```bash
npm install
npm run dev
```

For production:

```bash
python scripts/build.py --all  # Extract API docs, notebooks, and build indexes
npm run build
npm run preview
```

## Project Structure

```
src/
├── lib/
│   ├── api/               # API data system
│   │   ├── versions.ts    # Version loading utilities, manifest types
│   │   └── generated/     # TypeScript types (index.ts)
│   ├── components/
│   │   ├── api/           # API documentation components
│   │   │   ├── ModuleDoc.svelte
│   │   │   ├── ClassDoc.svelte
│   │   │   ├── FunctionDoc.svelte
│   │   │   ├── DocstringRenderer.svelte
│   │   │   ├── TypeRef.svelte
│   │   │   └── ApiToc.svelte
│   │   ├── common/        # Shared UI components
│   │   │   ├── Icon.svelte
│   │   │   ├── Tooltip.svelte
│   │   │   ├── CodeBlock.svelte
│   │   │   ├── NotebookCell.svelte
│   │   │   ├── MarkdownRenderer.svelte
│   │   │   └── RstRenderer.svelte
│   │   ├── layout/        # Page layout
│   │   │   ├── Header.svelte
│   │   │   ├── Sidebar.svelte      # Includes version selector
│   │   │   ├── MobileDrawer.svelte
│   │   │   └── DocLayout.svelte
│   │   ├── notebook/      # Jupyter notebook rendering
│   │   │   ├── Notebook.svelte
│   │   │   ├── CodeCell.svelte
│   │   │   ├── MarkdownCell.svelte
│   │   │   └── CellOutput.svelte
│   │   ├── examples/      # Examples page components
│   │   │   └── ExamplesToc.svelte
│   │   ├── search/        # Search UI components
│   │   │   ├── SearchInput.svelte
│   │   │   └── SearchResult.svelte
│   │   └── pages/         # Full page components
│   │       ├── PackageOverview.svelte
│   │       └── PackageApi.svelte
│   ├── config/            # Centralized configuration
│   │   ├── packages.ts    # Package metadata, links, features, installation
│   │   ├── pyodide.ts     # Python runtime config
│   │   └── links.ts       # External URLs
│   ├── notebook/          # Notebook parsing and loading
│   │   ├── types.ts
│   │   ├── parser.ts
│   │   └── loader.ts      # Version manifest and notebook loading
│   ├── pyodide/           # Python execution (Web Worker)
│   │   ├── index.ts       # Main thread bridge
│   │   ├── worker.ts      # Web Worker implementation
│   │   └── types.ts       # Message protocol types
│   ├── semantic/          # Semantic search (client-side)
│   │   ├── model.ts       # Embedding model loader (e5-small-v2)
│   │   ├── similarity.ts  # Cosine similarity search
│   │   └── index.ts       # Public API
│   ├── stores/            # Svelte stores
│   │   ├── apiContext.ts
│   │   ├── examplesContext.ts
│   │   ├── notebookStore.ts
│   │   ├── pyodideStore.ts
│   │   ├── versionStore.ts        # Per-package version persistence
│   │   ├── packageVersionsStore.ts # Pyodide package versions
│   │   ├── searchNavigation.ts
│   │   └── themeStore.ts
│   └── utils/
│       ├── search.ts      # Search with dynamic index loading
│       ├── crossref.ts    # Cross-reference linking
│       ├── codemirror.ts  # Editor setup
│       └── clipboard.ts
├── routes/
│   ├── +page.svelte       # Home (search, package cards)
│   ├── +layout.svelte     # Root layout
│   ├── pathsim/           # Static package routes (overview only)
│   │   └── +page.svelte
│   ├── chem/
│   │   └── +page.svelte
│   ├── vehicle/
│   │   └── +page.svelte
│   └── [package]/         # Dynamic versioned routes
│       ├── +layout.ts     # Package layout loader
│       ├── [version]/
│       │   ├── +layout.ts     # Version validation, manifest loading
│       │   ├── +layout.svelte # Version context provider
│       │   ├── api/
│       │   │   ├── +page.ts   # Load versioned API data
│       │   │   └── +page.svelte
│       │   └── examples/
│       │       ├── +page.ts   # Load versioned notebook list
│       │       ├── +page.svelte
│       │       └── [slug]/
│       │           ├── +page.ts   # Load versioned notebook
│       │           └── +page.svelte
└── app.css                # Global design system

scripts/
├── build.py               # Main build script (API, notebooks, indexes)
├── build-indexes.py       # Standalone index generation
├── build-embeddings.py    # Generate semantic search embeddings
├── rebuild-manifests.py   # Rebuild notebook manifests (metadata only)
├── requirements.txt
└── lib/
    ├── config.py          # Build configuration (min versions, paths)
    ├── api.py             # API extraction using Griffe
    ├── notebooks.py       # Notebook processing (incl. thumbnail extraction)
    ├── git.py             # Git operations (tags, checkout)
    └── executor.py        # Parallel execution utilities

static/
├── {package}/             # Per-package versioned content
│   ├── manifest.json      # Package manifest (versions, latest)
│   └── {tag}/             # Per-version content (e.g., v0.16.4)
│       ├── api.json           # API documentation
│       ├── manifest.json      # Notebook metadata (incl. thumbnails)
│       ├── search-index.json  # Versioned keyword search index
│       ├── crossref-index.json # Versioned crossref index
│       ├── embeddings-index.json # Versioned semantic search embeddings
│       ├── notebooks/         # Jupyter notebook files
│       ├── outputs/           # Pre-computed cell outputs
│       └── figures/           # Pre-rendered figures
└── *.png                  # Logo files
```

---

## Architecture Overview

### Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Python Packages │────>│ scripts/build.py│────>│ Per-Version     │
│ (pathsim, etc.) │     │ (Griffe)        │     │ Static Files    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        For each git tag:               v
                        ┌─────────────────────────────────────────┐
                        │ static/{package}/{tag}/                 │
                        │   ├── api.json                          │
                        │   ├── manifest.json (notebooks)         │
                        │   ├── search-index.json                 │
                        │   ├── crossref-index.json               │
                        │   ├── notebooks/                        │
                        │   └── figures/                          │
                        └─────────────────────────────────────────┘
```

### URL Scheme

| URL | Page |
|-----|------|
| `/` | Home with search and package cards |
| `/pathsim` | PathSim overview (features, installation) |
| `/pathsim/v0.16.4/api` | API reference (specific version) |
| `/pathsim/v0.16.4/examples` | Example notebooks gallery |
| `/pathsim/v0.16.4/examples/harmonic-oscillator` | Specific notebook |
| `/chem`, `/vehicle` | Other packages (same structure) |

### Key Abstractions

| Layer | Purpose | Key Files |
|-------|---------|-----------|
| **Build Script** | Extract API, notebooks, indexes | `scripts/build.py` |
| **Keyword Search** | Per-version search indexes | `search.ts`, `search-index.json` |
| **Semantic Search** | Natural language search via embeddings | `semantic/`, `embeddings-index.json` |
| **Cross-refs** | Per-version link resolution | `crossref.ts`, `TypeRef.svelte` |
| **Version Store** | Persist selected version per package | `versionStore.ts` |
| **Notebook Loader** | Fetch versioned notebooks | `loader.ts` |
| **Pyodide Worker** | Execute Python with versioned packages | `pyodide/worker.ts` |

---

## Build System

The main build script handles all content generation:

```bash
# Build specific package (smart mode - only missing versions)
python scripts/build.py --package pathsim

# Rebuild all versions for all packages
python scripts/build.py --all

# Build indexes only (for existing content)
python scripts/build-indexes.py
```

### What It Does

1. **API Extraction**: Uses Griffe to extract from Python source
2. **Notebook Processing**: Copies notebooks, extracts metadata
3. **Index Generation**: Creates search and crossref indexes per version
4. **Manifest Generation**: Creates package manifest with version list

### Configuration (`scripts/lib/config.py`)

```python
MIN_SUPPORTED_VERSIONS = {
    "pathsim": "0.7",
    "pathsim-chem": "0.1",
    "pathsim-vehicle": "0.1"
}
```

---

## Search System

Search uses per-version indexes loaded dynamically.

### Index Structure

Each version has its own `search-index.json`:

```json
[
  {
    "name": "Integrator",
    "type": "class",
    "moduleName": "pathsim.blocks.integrator",
    "path": "pathsim/v0.16.4/api#Integrator",
    "description": "Integration block for ODE systems"
  }
]
```

### Search Features

- **Multi-term queries**: Each term scored independently
- **Scoring hierarchy**: Exact match (100) > prefix (50) > contains (30) > description (10)
- **Type boosting**: Pages 1.5x, classes 1.2x, examples 1.15x
- **Keyboard shortcut**: Ctrl+F focuses search bar

---

## Semantic Search

In addition to keyword search, the documentation supports semantic search powered by Transformers.js running client-side.

### How It Works

1. **Build time**: `build-embeddings.py` generates embeddings for all API items and examples using e5-small-v2
2. **Load time**: Embeddings index loaded per-version from `embeddings-index.json`
3. **Query time**: User query embedded in browser, cosine similarity finds relevant results

### Embedding Index Structure

```json
{
  "items": [
    {
      "name": "Integrator",
      "type": "class",
      "path": "pathsim/v0.16.4/api#Integrator",
      "embedding": [0.012, -0.034, ...]
    }
  ]
}
```

### Features

- **Natural language queries**: "How do I integrate a signal?" finds `Integrator` class
- **Client-side inference**: No server required, runs in browser via ONNX Runtime
- **Lazy loading**: Model loaded only when semantic search is triggered
- **Combined results**: Semantic results merged with keyword search for best coverage

---

## Cross-Reference System

Automatically links class/function names in docstrings to their API documentation.

### Supported Patterns

```rst
:class:`Integrator`       # RST role syntax
`Integrator`              # Backtick code
'Integrator'              # Single-quoted names
```

### Per-Version Resolution

Cross-references resolve to the current version's API:

```
Integrator → /pathsim/v0.16.4/api#Integrator
```

---

## Versioned Documentation

Each package maintains historical API versions with full content.

### Package Manifest

Located at `static/{package}/manifest.json`:

```json
{
  "package": "pathsim",
  "latestTag": "v0.16.4",
  "versions": [
    {
      "tag": "v0.16.4",
      "released": "2025-01-17",
      "hasExamples": true
    },
    {
      "tag": "v0.9.0",
      "released": "2025-09-26",
      "hasExamples": false
    }
  ]
}
```

### Version Selection

- **Sidebar dropdown**: Shows all versions with "latest" badge
- **Persistence**: Selected version stored in localStorage per package
- **Smart navigation**: When switching to a version without examples, redirects to overview

---

## Interactive Notebooks

Jupyter notebooks run in the browser via Pyodide with versioned package support.

### Execution

- Pyodide runs in a Web Worker (non-blocking)
- **Versioned packages**: Installs specific version matching the docs (e.g., `pathsim==0.16.4`)
- Cell outputs rendered: text, images, HTML, errors
- Math support via KaTeX

### Keyboard Shortcuts

Jupyter-style keyboard shortcuts for code cells:

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Run cell and advance to next |
| `Ctrl+Shift+Enter` | Run cell (stay in place) |
| `Escape` | Unfocus current cell |

- Pressing `Ctrl+Enter` with no cell focused auto-selects the first code cell
- Focused cells show a highlight border for visibility
- Cells scroll into view when focused

### Example Thumbnails

Example tiles on the gallery page display thumbnails extracted from notebook figures:

- Extracted from the first `.. image::` (RST) or `![](...)` (Markdown) directive
- Falls back to description text if no figure found
- Thumbnails stored in version manifest metadata

### Version-Aware Execution

When viewing `/pathsim/v0.14.0/examples/...`, Pyodide installs `pathsim==0.14.0` to ensure examples work correctly with that version's API.

---

## Configuration

### Package Configuration (`src/lib/config/packages.ts`)

Central source of truth for all package metadata:

```typescript
export const packages = {
  pathsim: {
    id: 'pathsim',
    name: 'PathSim',
    description: 'Block-diagram simulation framework',
    logo: 'pathsim_logo.png',
    docs: 'pathsim',
    api: 'pathsim/api',
    examples: 'pathsim/examples',
    pypi: 'https://pypi.org/project/pathsim',
    conda: 'https://anaconda.org/conda-forge/pathsim',
    github: 'https://github.com/pathsim/pathsim',
    features: [...],
    installation: [
      { name: 'pip', command: 'pip install pathsim' },
      { name: 'conda', command: 'conda install -c conda-forge pathsim', minVersion: '0.14.0' }
    ],
    quickstart: { ... }
  }
};
```

### Pyodide Configuration (`src/lib/config/pyodide.ts`)

```typescript
export const PYODIDE_VERSION = '0.26.2';
export const PYTHON_PACKAGES = [
  { pip: 'pathsim', required: true, pre: true, import: 'pathsim' },
  { pip: 'matplotlib', required: true, pre: false, import: 'matplotlib' }
];
export const TIMEOUTS = { INIT: 120000, EXECUTION: 60000 };
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `npm run dev` | Start development server |
| `npm run build` | Production build |
| `npm run preview` | Preview production build |
| `npm run check` | TypeScript/Svelte type checking |
| `python scripts/build.py` | Build all content (smart mode) |
| `python scripts/build.py --all` | Rebuild all versions |
| `python scripts/build-indexes.py` | Regenerate search/crossref indexes |
| `python scripts/build-embeddings.py` | Generate semantic search embeddings |
| `python scripts/rebuild-manifests.py` | Update notebook metadata without re-execution |

---

## Design System

Global styles in `app.css` with CSS custom properties:

### Colors

| Variable | Dark | Light |
|----------|------|-------|
| `--surface` | #08080c | #f0f0f4 |
| `--surface-raised` | #1c1c26 | #ffffff |
| `--text` | #f0f0f5 | #1a1a1f |
| `--accent` | #0070c0 | #0070c0 |

### Typography

- **UI Font**: Inter
- **Code Font**: JetBrains Mono
- **Sizes**: 12px (base), 14px (md), 16px (lg)

### Components

- `.panel`, `.tile`, `.card` - Container styles
- `.elevated` - Subtle shadow effect
- `.crossref` - Cross-reference link styling

---

## Deployment

GitHub Pages deployment via GitHub Actions.

### Workflow

1. Clone PathSim repositories
2. Run `python scripts/build.py --all` (extracts API, notebooks, builds indexes)
3. Build SvelteKit (`npm run build`)
4. Deploy to GitHub Pages

### Scheduled Builds

Documentation is automatically rebuilt on a schedule to pick up new package releases:

- **Trigger**: GitHub Actions cron schedule (configurable)
- **Smart builds**: Only processes new git tags not already in static/
- **Auto-deploy**: New versions appear without manual intervention

### Environment Variables

- `BASE_PATH`: URL base path (e.g., `/pathsim-docs`)
