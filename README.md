# coreason-foundry

**The Collaborative Workspace Manager & Real-Time State Engine**

[![CI](https://github.com/CoReason-AI/coreason_foundry/actions/workflows/ci.yml/badge.svg)](https://github.com/CoReason-AI/coreason_foundry/actions/workflows/ci.yml)

`coreason-foundry` is the interactive, stateful backend for the CoReason IDE. It bridges the gap between fleeting engineering thoughts and permanent GxP artifacts.

## Documentation

Full documentation is available in the `docs/` directory and includes:

-   [**Product Requirements**](docs/product_requirements.md)
-   [**Architecture**](docs/architecture.md)
-   [**Usage Guide**](docs/usage.md)
-   [**Vignette**](docs/vignette.md)

## Getting Started

### Prerequisites

- Python 3.12+
- Poetry

### Installation

1.  Clone the repository:
    ```sh
    git clone https://github.com/CoReason-AI/coreason_foundry.git
    cd coreason_foundry
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
