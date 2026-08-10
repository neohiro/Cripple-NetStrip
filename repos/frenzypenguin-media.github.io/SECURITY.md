# Security Policy

## Supported Versions

| Branch  | Supported        |
| ------- | ---------------- |
| `main`  | ✅ Active         |
| `v1.x`  | ⚠️ Critical fixes only |
| `<v1`   | ❌ End of life    |

Only the latest release on the **Releases** page receives security updates.
Please upgrade before reporting an issue.

## Reporting a Vulnerability

**Please do not file a public issue.** Use one of the following private
channels:

1. **Preferred**: GitHub Security Advisories — open a *private* advisory from
   the **Security** tab of this repository.
2. **Email**: `security@neohiro.io` (PGP key on request).
3. **Signal / WhatsApp** (godadmin only, last resort): see
   `https://neohiro.github.io/contact/`.

You can expect an acknowledgement within **72 hours** and a triage decision
within **7 days**. Please give us a reasonable amount of time to investigate
and fix before any public disclosure.

## What to Include

A good vulnerability report contains:

- A clear, reproducible description of the issue
- Affected version(s) and commit hash(es)
- A minimal proof-of-concept (script, request, screenshot)
- Impact assessment (data exposure, RCE, privilege escalation, etc.)
- Your name / handle for credit (or "anonymous" if you prefer)

## Out of Scope

- Denial-of-service attacks that require sustained, high-volume traffic
- Issues only present in unsupported / archived branches
- Best-practice recommendations without a concrete exploit
- Self-XSS, clickjacking on unauthenticated pages
- Missing security headers that do not enable a concrete attack

## Recognition

We credit researchers in:

- The release notes of the fix
- `CREDITS.md` of this repository (under "Security acknowledgements")
- The [neohiro/security-hall-of-fame](https://github.com/neohiro) page

Monetary rewards are handled through the GitHub Sponsors bounty program when
available. See the sponsor button in this repository's README.

## Hardening Notes for Operators

- Pin versions by SHA, not by tag, in production deploys
- Run the container with `--read-only --cap-drop=ALL --security-opt=no-new-privileges`
- Mount secrets at runtime (never bake them into the image)
- Review `dependabot.yml` and merge security PRs within 7 days
- Subscribe to GitHub Security Advisories for this repo

---

Maintained by neohiro on behalf of the cross-org community.

---

Maintained by **[frenzypenguin-media](https://github.com/frenzypenguin-media)**.
