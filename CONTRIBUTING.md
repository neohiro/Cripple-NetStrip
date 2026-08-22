# Contributing to **Cripple-NetStrip**

Thanks for helping out! This project accepts issues and pull requests.

## Reporting bugs

Open a **Bug report** issue and fill in every field of the form - OS version,
app version and reproduction steps make the difference between a fix and a
close. For anything you believe is exploitable, use **Report a vulnerability**
on the Security tab instead (see SECURITY.md).

## Development setup

```bash
pip install -r requirements.txt
pip install -e .
python -m pytest tests/
flake8 netstrip/ --count --select=E9,F63,F7,F82 --show-source
python main.py
```

Android builds use `buildozer` (see buildozer.spec); CI covers lint, import smoke tests and unit tests on three OSes.

## Code layout

`netstrip/` is fully modular: `core/` (engine, DNS proxy, blocklist manager,
interceptor), `gui/views/`, `platform/`, `data/`. Entry point is `main.py`.
Please match the existing module boundaries rather than growing monoliths.

## Pull requests

1. Fork and create a topic branch.
2. Keep changes focused - one fix or feature per PR.
3. Test against the live target (Windows / grid) before submitting where feasible.
4. Describe **what** and **why** in the PR body.

## Contact

[frenzypenguin.media](https://linktr.ee/frenzypenguin.media)

## Releasing

1. Bump the version (code constant / README).
2. Commit and push.
3. **Draft a new Release** on GitHub with tag `vX.Y.Z` and publish it - CI
   builds every platform binary automatically and attaches them; release
   notes are generated from merged commits since the last tag.