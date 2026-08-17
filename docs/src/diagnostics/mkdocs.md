# MkDocs diagnostics

Return code: `0`

Issues: `3`

## Command

```text
C:\Users\PARABOT\Documents\git_CR\py-doc-tools\.pixi\envs\default\python.exe -m mkdocs build -f C:\Users\PARABOT\Documents\git_CR\py-doc-tools\mkdocs.yml
```

## Parsed issues

| Code | File | Line | Message |
|---|---|---:|---|
| `FALLBACK` | `` | 0 | A reference to 'index.md' is included in the 'nav' configuration, which is not found in the documentation files. |
| `FALLBACK` | `` | 0 | A reference to 'todo.md' is included in the 'nav' configuration, which is not found in the documentation files. |
| `FALLBACK` | `` | 0 | A reference to 'diagnostics/mkdocs.md' is included in the 'nav' configuration, which is not found in the documentation files. |

## Raw output

```text
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: C:\Users\PARABOT\Documents\git_CR\py-doc-tools\docs\build
WARNING -  A reference to 'index.md' is included in the 'nav' configuration, which is not found in the documentation files.
WARNING -  A reference to 'todo.md' is included in the 'nav' configuration, which is not found in the documentation files.
WARNING -  A reference to 'diagnostics/mkdocs.md' is included in the 'nav' configuration, which is not found in the documentation files.
INFO    -  Documentation built in 1.17 seconds
```
