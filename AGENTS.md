# Repository Guidelines

## Project Structure & Module Organization

This repository is currently minimal and contains only the root `README.md`. As implementation is added, keep the layout predictable:

- `src/`: application source code, RAG pipelines, data loaders, retrievers, and analysis modules.
- `tests/`: automated tests mirroring the `src/` package structure.
- `data/`: local sample inputs only; avoid committing large, private, or generated datasets.
- `docs/`: design notes, architecture decisions, and usage examples.
- `assets/`: static images, diagrams, or other non-code resources.

Place modules near the domain they support instead of creating broad utility files prematurely.

## Build, Test, and Development Commands

No build system or package manager is configured yet. Add commands when tooling is introduced. Recommended examples:

- `python -m pytest`: run the full test suite.
- `python -m pytest tests/test_retriever.py`: run a focused test file.
- `python -m ruff check src tests`: lint Python code.
- `python -m ruff format src tests`: format Python code.

If another stack is adopted, document exact setup and execution commands in `README.md`.

## Coding Style & Naming Conventions

Prefer clear, typed, modular code. For Python, use `snake_case.py` filenames, `snake_case` functions and variables, `PascalCase` classes, and 4-space indentation. Name public functions after the real estate or RAG concept they implement, for example `build_price_retriever`.

Use structured parsers and library APIs for documents, embeddings, and tabular data where possible. Keep configuration in explicit files or environment variables, not hard-coded paths.

## Testing Guidelines

Add tests for new data transformations, retrieval steps, prompt construction paths, and analysis rules. Use `tests/test_<module>.py` naming and descriptive test functions such as `test_filters_transactions_by_region`.

Prefer small fixtures with anonymized or synthetic real estate records. Do not commit production data, API keys, model outputs containing private text, or large generated artifacts.

## Commit & Pull Request Guidelines

The current history contains only `Initial commit`, so no detailed convention has emerged. Use short, imperative commit messages such as `Add transaction loader` or `Document local setup`.

Pull requests should include a concise summary, testing performed, new configuration variables, and screenshots or sample outputs when behavior changes. Link related issues when available and call out data or model assumptions.

## Security & Configuration Tips

Keep secrets in environment variables or ignored local files. Document required variables with safe placeholders, for example `OPENAI_API_KEY=<your-key>`. Never commit raw property records, personal data, credentials, or paid API responses.
