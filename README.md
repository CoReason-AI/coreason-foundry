# coreason-foundry

**The Collaborative Workspace Manager & Real-Time State Engine**

[![CI](https://github.com/CoReason-AI/coreason-foundry/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/CoReason-AI/coreason-foundry/actions/workflows/ci-cd.yml)
[![Docker](https://github.com/CoReason-AI/coreason-foundry/actions/workflows/docker.yml/badge.svg)](https://github.com/CoReason-AI/coreason-foundry/actions/workflows/docker.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/coreason_foundry.svg)](https://pypi.org/project/coreason_foundry)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/coreason_foundry.svg)](https://pypi.org/project/coreason_foundry)
[![License](https://img.shields.io/badge/license-Prosperity--3.0-blue)](https://github.com/CoReason-AI/coreason-foundry/blob/main/LICENSE)
[![codecov](https://codecov.io/gh/CoReason-AI/coreason-foundry/graph/badge.svg)](https://codecov.io/gh/CoReason-AI/coreason-foundry)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

`coreason-foundry` is the interactive, stateful backend for the CoReason IDE. It bridges the gap between fleeting engineering thoughts and permanent GxP artifacts.

## Documentation

Full documentation is available in the `docs/` directory and includes:

-   [**Product Requirements**](docs/product_requirements.md)
-   [**Architecture**](docs/architecture.md)
-   [**Usage Guide**](docs/usage.md)
-   [**Vignette**](docs/vignette.md)
-   [**Requirements**](requirements.md)

## Getting Started

### Prerequisites

- Python 3.12+
- Poetry

### Installation

1.  Clone the repository:
    ```sh
    git clone https://github.com/CoReason-AI/coreason-foundry.git
    cd coreason-foundry
    ```
2.  Install dependencies:
    ```sh
    poetry install
    ```

### Development

-   Run the linter:
    ```sh
    poetry run pre-commit run --all-files
    ```
-   Run the tests:
    ```sh
    poetry run pytest
    ```
-   Build the documentation:
    ```sh
    poetry run mkdocs build
    ```
