<h1 align="center"> NeatPush </h1>

<p align="center">
  <a href="https://github.com/gjeusel/neatpush/actions?query=workflow%3ACI+branch%3Amain">
      <img src="https://github.com/gjeusel/neatpush/workflows//CI/badge.svg?event=push&branch=main" alt="Test Suite" onerror="this.style.display='none'">
  </a>
  <a href="https://coverage-badge.samuelcolvin.workers.dev/redirect/gjeusel/neatpush" alt="Test Coverage" onerror="this.style.display='none'">
      <img src="https://coverage-badge.samuelcolvin.workers.dev/gjeusel/neatpush.svg" alt="Coverage">
  </a>
  <a href="https://pypi.org/project/neatpush/">
      <img src="https://badge.fury.io/py/neatpush.svg" alt="Package version" onerror="this.style.display='none'">
  </a>
  <a href="https://gjeusel.github.io/neatpush/">
    <img src="https://img.shields.io/badge/mkdocs-pages-brightgreen" alt="MKDocs github page">
  </a>
  <a href="https://github.com/pre-commit/pre-commit">
      <img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" alt="pre-commit">
  </a>
</p>

<p align="center">
  <em>Notify me of new manga chapters.</em>
</p>

---

## Installation

```bash
pip install neatpush
```

### Developper

##### Install

```bash
make install
```

##### Launch tests:

```bash
pytest
```

##### Write docs:

```bash
mkdocs serve --watch .
```

### Update Cookiecutter Template

```bash
cruft update --skip-apply-ask --allow-untracked-files --project-dir .
```

