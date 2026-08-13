# py-doc-tools

`py-doc-tools` is a small, typed and configurable documentation tooling package for Python projects using MkDocs.

It provides a single CLI, `pydocs`, to generate API documentation pages, inject generated navigation blocks into `mkdocs.yml`, run coverage reports, and execute MkDocs commands.

The package is designed to be reused across several Python repositories with a shared documentation workflow.

---

## Features

Current V1 features:

- Generate MkDocs API reference pages from Python packages.
- Generate `mkdocstrings`-compatible Markdown pages.
- Inject generated API navigation into `mkdocs.yml` between explicit markers.
- Generate HTML coverage reports with `pytest-cov`.
- Run `mkdocs build`.
- Run `mkdocs serve`.
- Read configuration from `pyproject.toml`.
- Resolve paths from the project root.
- Provide a typed and testable codebase.
- Support Python 3.12.
- Keep console output clean and CI-friendly.


---

## Requirements

`py-doc-tools` requires:

```text
Python >= 3.12
```

The package itself has no required runtime dependency for the V1 core.

However, depending on the commands you run in the consuming project, you should install:

```text
mkdocs
mkdocstrings
mkdocstrings-python
pytest
pytest-cov
```

These tools are intentionally expected to be installed by the consuming project. This avoids dependency conflicts between repositories.

---

## Installation

### Local editable installation

During development, from a consuming project:

```toml
[pypi-dependencies]
py-doc-tools = { path = "C:/Users/cleme/Documents/GitLab_Perso/dev-tools-cr/python/py-doc-tools", editable = true }
```

Or inside a Pixi feature:

```toml
[feature.dev.pypi-dependencies]
py-doc-tools = { path = "C:/Users/cleme/Documents/GitLab_Perso/dev-tools-cr/python/py-doc-tools", editable = true }
```

### Git installation

Once pushed to GitLab:

```toml
[pypi-dependencies]
py-doc-tools = { git = "https://gitlab.com/dev-tools-cr/python/py-doc-tools.git", branch = "main" }
```

---

## CLI

The package exposes the `pydocs` command.

```bash
pydocs --help
```

### Generate API documentation

```bash
pydocs generate --api
```

This command:

1. Scans configured Python packages.
2. Generates Markdown pages under the configured API output directory.
3. Creates `mkdocstrings` directives.
4. Injects the generated navigation block into `mkdocs.yml`.

---

### Generate coverage report

```bash
pydocs generate --coverage
```

This command runs:

```bash
python -m pytest --cov=<package> --cov-report html:<output_dir>
```

using the configured package and output directory.

---

### Run all enabled generators

```bash
pydocs generate --all
```

This command runs every enabled generator from the configuration.

For V1, this can include:

- API documentation generation;
- coverage generation;
- `mkdocs build`.

---

### Run MkDocs build

```bash
pydocs mkdocs build
```

Strict mode:

```bash
pydocs mkdocs build --strict
```

---

### Run MkDocs serve

```bash
pydocs mkdocs serve
```

---

### Clean generated API documentation

```bash
pydocs clean api
```

---

### Use a custom project root

By default, `pydocs` uses the current directory as the project root.

You can override it:

```bash
pydocs --root path/to/project generate --api
```

Verbose mode:

```bash
pydocs --verbose generate --api
```

---

## Configuration

Configuration is read from the consuming project's `pyproject.toml`.

The root table is:

```toml
[tool.py-doc-tools]
```

### Minimal configuration

```toml
[tool.py-doc-tools]
docs_dir = "docs"
docs_src_dir = "docs"
mkdocs_config = "mkdocs.yml"
packages = ["my_package"]

enable_api = true
enable_coverage = false

use_emojis = false
console_emojis = false
verbose = false

[tool.py-doc-tools.api]
output_dir = "docs/api"
nav_start_marker = "# --- AUTOGEN_API_START ---"
nav_end_marker = "# --- AUTOGEN_API_END ---"
clean_output_dir = true
overview_enabled = false
folder_intro_enabled = false
exclude_dirs = [
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".pixi",
]
exclude_files = [
    "__init__.py",
    "test_*.py",
]
```

---

## MkDocs markers

`py-doc-tools` injects generated navigation between explicit markers.

Example `mkdocs.yml`:

```yaml
site_name: My Project

nav:
  - Home: index.md
  - API:
    # --- AUTOGEN_API_START ---
    - My Package:
      - Client: api/my_package/client.md
      - Models: api/my_package/models.md
    # --- AUTOGEN_API_END ---

```

After running:

```bash
pydocs generate --api
```

the block between the markers is replaced.

Example generated output:

```yaml
site_name: My Project

nav:
  - Home: index.md
  - API:
      # --- AUTOGEN_API_START ---
      - My Package:
          - Client: api/my_package/client.md
          - Models: api/my_package/models.md
    # --- AUTOGEN_API_END ---
```

The markers must remain in the file.

---

## API documentation generation

For each configured package, `py-doc-tools` scans Python files and generates Markdown pages containing `mkdocstrings` directives.

For example, this file:

```text
my_package/client.py
```

generates:

```text
docs/api/my_package/client.md
```

with content similar to:

```markdown
# Client

::: my_package.client
```

---

## Optional API overview

Enable an API overview page:

```toml
[tool.py-doc-tools.api]
overview_enabled = true
```

This creates:

```text
docs/api/api_overview.md
```

and adds it to the generated navigation.

---

## Optional folder introductions

Folder introductions can be enabled:

```toml
[tool.py-doc-tools.api]
folder_intro_enabled = true
folder_intro_filename = "__doc__.md"
```

When enabled, each package or subfolder can provide a local Markdown intro file:

```text
my_package/__doc__.md
my_package/submodule/__doc__.md
```

These files are used to generate intro pages in the API documentation.

---

## Optional module pre/post content

Each Python module can have optional companion Markdown files:

```text
client.pre.md
client.post.md
```

For:

```text
client.py
```

`client.pre.md` is inserted before the `mkdocstrings` directive, and `client.post.md` is inserted after it.

Example:

```text
my_package/client.py
my_package/client.pre.md
my_package/client.post.md
```

Generated page:

```markdown
# Client

Content from client.pre.md

::: my_package.client

Content from client.post.md
```

---

## Coverage configuration

Enable coverage generation:

```toml
[tool.py-doc-tools]
enable_coverage = true

[tool.py-doc-tools.coverage]
package = "my_package"
output_dir = "docs/coverage"
branch = true
quiet = true
```

Run:

```bash
pydocs generate --coverage
```

If `package` is not provided, the first package from `packages` is used.

---

## Complete example for a simple project

```toml
[tool.py-doc-tools]
docs_dir = "docs"
docs_src_dir = "docs"
mkdocs_config = "mkdocs.yml"
packages = ["my_package"]

use_emojis = false
console_emojis = false
verbose = false

enable_api = true
enable_coverage = true

[tool.py-doc-tools.api]
output_dir = "docs/api"
nav_start_marker = "# --- AUTOGEN_API_START ---"
nav_end_marker = "# --- AUTOGEN_API_END ---"
clean_output_dir = true
overview_enabled = false
folder_intro_enabled = false
exclude_dirs = [
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".pixi",
    ".venv",
    "venv",
    "build",
    "dist",
]
exclude_files = [
    "__init__.py",
    "test_*.py",
]

[tool.py-doc-tools.coverage]
package = "my_package"
output_dir = "docs/coverage"
branch = true
quiet = true
```

---

## Example Pixi tasks for consuming projects

```toml
[tasks]
docs-api = "pydocs generate --api"
docs-coverage = "pydocs generate --coverage"
docs-generate = "pydocs generate --all"
docs-build = "pydocs mkdocs build"
docs-build-strict = "pydocs mkdocs build --strict"
docs-serve = "pydocs mkdocs serve"
docs-clean-api = "pydocs clean api"
```

Usage:

```bash
pixi run docs-api
pixi run docs-build
pixi run docs-serve
```

---

## Development

Install the development environment:

```bash
pixi install
```

Run formatting:

```bash
pixi run fmt
```

Run linting:

```bash
pixi run lint
```

Run typing checks:

```bash
pixi run typecheck
```

Run tests:

```bash
pixi run tests
```

Run the full check pipeline:

```bash
pixi run check
```

---

## Quality gates

The project is developed with:

- Python 3.12;
- Ruff formatting;
- Ruff linting;
- mypy strict mode;
- pytest;
- pytest-cov;
- branch coverage.

Current quality target:

```text
coverage >= 90%
```

Typical current coverage is above 95%.

---

## Repository structure

```text
py-doc-tools/
├── pyproject.toml
├── pixi.toml
├── README.md
├── src/
│   └── py_doc_tools/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── api/
│       ├── config/
│       ├── core/
│       ├── coverage/
│       ├── mkdocs/
│       └── pipeline/
└── tests/
```

---

## Design principles

`py-doc-tools` follows a few important principles:

1. **Project-agnostic behavior**  
   No dependency on a specific repository layout beyond explicit configuration.

2. **Configuration over hardcoded paths**  
   All project-specific behavior should be defined in `pyproject.toml`.

3. **Typed implementation**  
   The codebase is designed to pass strict typing checks.

4. **Small composable commands**  
   CLI commands should be clear rather than overly short.

5. **No hidden source modification by default**  
   V1 does not modify source files.

6. **CI-friendly output**  
   Console output is intentionally simple and stable.

---

## License

This project is distributed under the MIT License with an additional
no-endorsement clause.

See [`LICENSE`](LICENSE) for details.
