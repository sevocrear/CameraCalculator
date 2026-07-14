# Contributing

Thank you for improving CameraCalculator.

## Development setup

Use Python 3.12 or newer and [uv](https://docs.astral.sh/uv/):

```bash
uv sync --frozen --all-extras
uv run ruff check .
uv run pytest -m 'not ui'
```

For browser tests, start the application in one terminal:

```bash
uv run uvicorn cctv_lens_calc.api.main:app --port 8000
```

Then run the UI suite in another:

```bash
uv run playwright install chromium
BASE_URL=http://127.0.0.1:8000 uv run pytest -m ui
```

The complete containerized suite is:

```bash
./scripts/ci.sh
```

## Change guidelines

- Keep projection and metric logic in `src/cctv_lens_calc/domain/`.
- Add or update tests for behavior changes.
- Treat API projection results as authoritative; UI geometry is explanatory.
- Document assumptions, especially lens projection models and FOV limits.
- Run Ruff and the relevant pytest suites before opening a pull request.
- Update `uv.lock` when dependencies in `pyproject.toml` change.

By contributing, you agree that your contribution is licensed under the
[MIT License](LICENSE). Third-party assets must include compatible terms and
complete attribution in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
