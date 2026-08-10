---
title: auto-resume
tagline: "Self-healing OpenCode sessions — automatic retries, model rotation on quota/outages, permission autopilot & walk-away task autonomy"
platform: Cross-platform (Node.js)
language: TypeScript
category: Developer Tools
repo_url: https://github.com/neohiro/auto-resume
featured: true
weight: 6
icon: |
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <path d="M21 12a9 9 0 11-6.219-8.56" stroke="var(--cyan)" stroke-width="2"/>
    <path d="M21 3v5h-5" stroke="var(--cyan)" stroke-width="2"/>
    <path d="M12 12a5 5 0 10-5-5" stroke="var(--cyan)" stroke-width="1.5" opacity="0.5"/>
  </svg>
---
**auto-resume** is an OpenCode plugin that makes your AI coding sessions resilient to interruptions.

## Features

- **Automatic Retries** — Detects rate limits, quota exhaustion, network errors, and model outages; retries with exponential backoff
- **Model Rotation** — Seamlessly switches between models (GPT-4, Claude, etc.) when one hits limits
- **Permission Autopilot** — Handles permission prompts automatically for safe operations
- **Walk-Away Autonomy** — Long-running tasks continue unattended; recovers from crashes automatically

## Installation

```bash
# Via OpenCode plugin system
opencode plugin install neohiro/auto-resume
```

## How It Works

The plugin wraps OpenCode's execution pipeline with a resilience layer:

1. **Error Classification** — Categorizes failures as retryable (rate limits, timeouts) vs. non-retryable (syntax errors, logic bugs)
2. **State Persistence** — Checkpoints conversation state every N turns to survive restarts
3. **Model Pool** — Maintains a prioritized list of fallback models with capability matching
4. **Permission Profiles** — Pre-approves safe operations (file reads, searches) while prompting for risky ones

## Configuration

```json
{
  "autoResume": {
    "maxRetries": 5,
    "baseDelayMs": 2000,
    "maxDelayMs": 60000,
    "modelPool": ["gpt-4o", "claude-3.5-sonnet", "gpt-4-turbo"],
    "permissionProfile": "balanced"
  }
}
```

## Use Cases

- **Overnight refactoring** — Start a large refactor before bed, wake up to completed work
- **CI/CD pipelines** — Run OpenCode in automated pipelines without manual intervention
- **Unreliable networks** — Mobile/hotspot development where connections drop
- **Multi-model workflows** — Use best model per task, auto-fallback on limits

## Requirements

- OpenCode v0.8+
- Node.js 18+
- Valid API keys for at least one model in the pool

## Related

- [OpenCode Documentation](https://opencode.ai)
- [Plugin Development Guide](https://opencode.ai/docs/plugins)