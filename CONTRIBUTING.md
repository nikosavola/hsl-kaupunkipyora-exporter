# Contributing

Thanks for your interest in improving HSL Kaupunkipyörä Exporter.

## Before you start

- Search existing [issues](https://github.com/nikosavola/hsl-kaupunkipyora-exporter/issues) and pull requests to avoid duplicate work.
- For larger changes, open or comment on an issue first so the approach can be discussed.
- Keep pull requests focused. Please avoid unrelated cleanup in the same PR.

## Development setup

This project uses Python 3.13+, [`uv`](https://docs.astral.sh/uv/), and [`just`](https://github.com/casey/just).

```bash
git clone https://github.com/nikosavola/hsl-kaupunkipyora-exporter.git
cd hsl-kaupunkipyora-exporter
just install
```

## Common tasks

Run the test suite:

```bash
just test
```

If you are changing formatting or lint-sensitive files, run the relevant project checks before opening a pull request.

## Pull requests

1. Fork the repository and create a branch from `main`.
2. Make the smallest change that solves the issue.
3. Add or update tests when behavior changes.
4. Update documentation when needed.
5. Open a pull request with a clear description of the problem and solution.

## Commit messages

Short, descriptive commit messages are preferred. For example:

```text
fix: resolve issue #6
```

## Code of conduct

By participating in this project, you agree to follow the guidelines in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
