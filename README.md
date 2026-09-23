# py-doc-tools

`py-doc-tools` is a typed and configurable documentation generator for Python projects using MkDocs.

It provides a single CLI, `pydocs`, to generate and maintain:

- API documentation with `mkdocstrings`;
- examples with downloadable inputs, outputs and image previews;
- coverage reports;
- TODO/FIXME reports;
- Ruff and MkDocs diagnostics;
- class diagrams;
- README pages;
- generated MkDocs navigation.

Configuration is read from the consuming project's `pyproject.toml`.

---

## Features

- Generate API reference pages from Python packages.
- Generate example pages from files or directories.
- Copy example assets while preserving their directory structure.
- Display image previews and downloadable files.
- Generate coverage, diagnostics, TODO and class-diagram pages.
- Inject navigation blocks into `mkdocs.yml`.
- Run `mkdocs build` and `mkdocs serve`.
- Inject and clean generated source tags.
- Support nested packages and example directories.
- Provide typed, tested and CI-friendly tooling.
- Support Python 3.12 and later.

---

## Requirements

`py-doc-tools` requires:

```text
Python >= 3.12
```

The consuming project should install the tools needed by its documentation workflow:

```text
mkdocs
mkdocstrings
mkdocstrings-python
pytest
pytest-cov
ruff
```

Optional features may require additional MkDocs plugins or diagram tools.

### Image preview requirement

Generated example previews use Markdown attributes to control image size and layout.

Add `attr_list` to the consuming project's `mkdocs.yml`:

```yaml
markdown_extensions:
  - attr_list
```

If `markdown_extensions` already exists, add `attr_list` to the existing list.

Example:

```yaml
markdown_extensions:
  - admonition
  - attr_list
  - pymdownx.details
  - pymdownx.superfences
```

Without `attr_list`, images can still be linked, but preview attributes such as the maximum width will not be interpreted correctly.

---

## Installation

### From GitLab

With Pixi:

```toml
[feature.dev.pypi-dependencies]
py-doc-tools = {
    git = "https://gitlab.com/dev-tools-cr/python/py-doc-tools.git",
    branch = "main"
}
```

### Local editable installation

```toml
[feature.dev.pypi-dependencies]
py-doc-tools = {
    path = "../py-doc-tools",
    editable = true
}
```

The dependency can also be declared under `[pypi-dependencies]` when Pixi features are not used.

---

## Quick start

### 1. Install the required documentation tools

Example Pixi configuration:

```toml
[feature.dev.dependencies]
mkdocs = ">=1.6,<2"
mkdocstrings = ">=1,<2"
mkdocstrings-python = ">=2,<3"
pytest = ">=9,<10"
pytest-cov = ">=7,<8"
ruff = "*"

[feature.dev.pypi-dependencies]
py-doc-tools = {
    git = "https://gitlab.com/dev-tools-cr/python/py-doc-tools.git",
    branch = "main"
}
```

### 2. Configure `mkdocs.yml`

```yaml
site_name: My Project

docs_dir: docs/src
site_dir: docs/build/site

markdown_extensions:
  - attr_list

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths:
            - src

nav:
  - Home: index.md

  - API:
      # --- AUTOGEN_API_START ---
      # --- AUTOGEN_API_END ---

  - Examples:
      # --- AUTOGEN_EXAMPLES_START ---
      # --- AUTOGEN_EXAMPLES_END ---
```

The marker lines must remain in the file. Content between them is generated automatically.

### 3. Configure `pyproject.toml`

```toml
[tool.py-doc-tools]
docs_dir = "docs"
docs_src_dir = "docs/src"
mkdocs_config = "mkdocs.yml"
packages = ["my_package"]

enable_api = true
enable_examples = true
enable_coverage = false
enable_readme = false
enable_todo = true
enable_diagnostics = true
enable_tags = false
enable_diagrams = false

use_emojis = true
console_emojis = false
verbose = false
```

### 4. Generate and serve the documentation

```bash
pydocs generate --all
mkdocs serve
```

Then open:

```text
http://127.0.0.1:8000/
```

---

## CLI

Display the available commands:

```bash
pydocs --help
```

### Generate documentation

Generate all enabled sections:

```bash
pydocs generate --all
```

Generate individual sections:

```bash
pydocs generate --api
pydocs generate --examples
pydocs generate --coverage
pydocs generate --todo
pydocs generate --diagnostics
pydocs generate --diagrams
pydocs generate --readme
```

Available options depend on the installed version. Use:

```bash
pydocs generate --help
```

### MkDocs

```bash
pydocs mkdocs build
pydocs mkdocs build --strict
pydocs mkdocs serve
```

### Custom project root

```bash
pydocs --root path/to/project generate --all
```

### Verbose mode

```bash
pydocs --verbose generate --all
```

---

## API documentation

Basic configuration:

```toml
[tool.py-doc-tools.api]
output_dir = "docs/src/api"

nav_start_marker = "# --- AUTOGEN_API_START ---"
nav_end_marker = "# --- AUTOGEN_API_END ---"

clean_output_dir = true
overview_enabled = true

folder_intro_enabled = true
folder_intro_filename = "__doc__.md"

module_pre_suffix = ".pre.md"
module_post_suffix = ".post.md"

exclude_dirs = [
    "__pycache__",
    ".git",
    ".pixi",
    ".venv",
    "tests",
    "docs",
    "build",
    "dist",
]

exclude_files = [
    "__init__.py",
    "*.pyc",
]
```

For a module such as:

```text
src/my_package/client.py
```

the generator creates a page containing a `mkdocstrings` directive:

```markdown
# Client

::: my_package.client
```

### Folder introductions

When enabled, folders can provide an introduction file:

```text
src/my_package/__doc__.md
src/my_package/subpackage/__doc__.md
```

### Module pre/post content

Additional content can be placed around the generated API directive:

```text
client.pre.md
client.py
client.post.md
```

---

## Examples documentation

Directory mode generates one page for each detected example directory.

Recommended configuration:

```toml
[tool.py-doc-tools.examples]
source_dir = "examples"
output_dir = "docs/src/examples"
assets_dir = "docs/src/examples/assets"

nav_start_marker = "# --- AUTOGEN_EXAMPLES_START ---"
nav_end_marker = "# --- AUTOGEN_EXAMPLES_END ---"

mode = "directory"
overview_enabled = true
clean_output_dir = true

copy_assets = true
show_image_previews = true
preview_max_width_px = 800

skip_dirs = [
    "__pycache__",
    ".git",
    ".pixi",
    ".pytest_cache",
]

skip_files = [
    "*.pyc",
    "*.pyo",
]

asset_extensions = [
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".pdf",
]
```

Example layout:

```text
examples/
└── demo/
    ├── demo.py
    ├── README.md
    ├── demo.inputs/
    │   └── input.csv
    └── demo.outputs/
        ├── result.json
        └── plot.png
```

The generated page includes:

- the example description;
- the main script and execution command;
- downloadable input and output files;
- reduced image previews;
- preserved nested output directories.

Remember to enable `attr_list` in `mkdocs.yml`:

```yaml
markdown_extensions:
  - attr_list
```

---

## Coverage

Enable coverage generation:

```toml
[tool.py-doc-tools]
enable_coverage = true

[tool.py-doc-tools.coverage]
package = "my_package"
output_dir = "docs/build/coverage"
page_file = "docs/src/coverage-report.md"

branch = true
quiet = true

nav_enabled = true
inject_backlinks = true
```

Run:

```bash
pydocs generate --coverage
```

The consuming project must provide `pytest` and `pytest-cov`.

---

## TODO and diagnostics

### TODO/FIXME report

```toml
[tool.py-doc-tools.todo]
output_file = "docs/src/todo.md"

scan_roots = [
    "src",
    "tests",
    "examples",
]

markers = [
    "TODO",
    "FIXME",
    "BUG",
    "HACK",
]

mode = "sections"
```

### Ruff and MkDocs diagnostics

```toml
[tool.py-doc-tools.diagnostics]
output_dir = "docs/src/diagnostics"
ruff_output_file = "docs/src/diagnostics/ruff.md"
mkdocs_output_file = "docs/src/diagnostics/mkdocs.md"

enable_ruff = true
enable_mkdocs = true
mkdocs_strict = false

fail_on_ruff = false
fail_on_mkdocs = false
```

---

## Class diagrams

Enable class-diagram generation:

```toml
[tool.py-doc-tools]
enable_diagrams = true

[tool.py-doc-tools.diagrams]
output_file = "docs/src/diagrams/classes.md"

scan_roots = [
    "src/my_package",
]

include_private = false
```

Diagram generation may require optional tools depending on the configured output format.

---

## Source tags

Generated tags can associate TODO or diagnostic entries with source files.

Example configuration:

```toml
[tool.py-doc-tools.tags]
scan_roots = [
    "src",
    "tests",
    "examples",
]

markers = [
    "TODO",
    "FIXME",
    "BUG",
    "HACK",
]

generated_prefix = "py-doc-tools"
dry_run = false
```

Common commands:

```bash
pydocs tags inject
pydocs tags inject --write
pydocs tags inject --dry-run

pydocs tags clean
pydocs tags clean --write
pydocs tags clean --dry-run
```

---

## Pixi tasks

Example tasks for a consuming project:

```toml
[feature.dev.tasks]
docs = "pydocs generate --all"
docs-build = "mkdocs build"
docs-build-strict = "mkdocs build --strict"
docs-serve = "pydocs generate --all && mkdocs serve"

docs-tags-inject = "pydocs tags inject --write"
docs-tags-clean = "pydocs tags clean --write"
```

Usage:

```bash
pixi run -e dev docs
pixi run -e dev docs-build
pixi run -e dev docs-serve
```

---

## Development

Install the environment:

```bash
pixi install
```

Run the checks:

```bash
pixi run tests
pixi run lint
pixi run format-check
pixi run typecheck
```

Run the complete validation pipeline:

```bash
pixi run check
```

---

## Repository structure

```text
py-doc-tools/
├── docs/
│   ├── src/
│   └── build/
├── src/
│   └── py_doc_tools/
│       ├── api/
│       ├── config/
│       ├── core/
│       ├── coverage/
│       ├── diagnostics/
│       ├── diagrams/
│       ├── examples/
│       ├── mkdocs/
│       ├── pipeline/
│       ├── readme/
│       ├── tags/
│       └── todo/
├── tests/
├── mkdocs.yml
├── pixi.toml
├── pyproject.toml
└── README.md
```

Generated documentation under `docs/build/` should normally be excluded from Git.

---

## Design principles

- **Configuration over hardcoded paths**
- **Project-independent behavior**
- **Typed and testable implementation**
- **Deterministic generated files**
- **Explicit MkDocs navigation markers**
- **CI-friendly commands and output**
- **No source modification unless explicitly requested**

---

## License

This project is distributed under the X11 License.

See [`LICENSE`](LICENSE) for details.
