---
layout: default
title: Terms of Service
description: "Terms of Service — neohiro infrastructure"
permalink: /tos/
---

# Terms of Service

**Effective: January 1, 2026**  
**Operator: FrenzyPenguin Media** (`contact@frenzypenguin.media`)  
**Applicable law: Belgium / European Union**

---

## 1. Acceptance

By accessing or using any neohiro infrastructure, you agree to these Terms of Service ("Terms").
If you do not agree, do not use the service.

---

## 2. Services Covered

These Terms apply to all neohiro open-source infrastructure and tooling, including:

- **neohiro/wingman-hub** — autonomous digital assistant stack
- **neohiro/private-assistant** — personal AI chief-of-staff
- **neohiro/Brain** — entity knowledge and heartbeat system
- **neohiro/Heart** — cadence engine and self-healing infrastructure
- **neohiro/Mouth** — LLM output and natural-language interface
- All associated tooling, scripts, Docker containers, and GitHub Actions

---

## 3. Acceptable Use

You may use this infrastructure for:

- Personal and commercial automation
- Self-hosting on your own systems
- Educational and research purposes
- Integration in open-source projects (GPL-3.0 compliance required)

You may **not** use this infrastructure for:

- Spam, harassment, or social engineering
- Autonomous weapons or surveillance of individuals without consent
- Phishing or credential theft
- Circumventing security controls of third parties
- Any activity that violates applicable law

---

## 4. Privacy

Your privacy is respected. See our [/privacy](/privacy/) page for full details.

**In brief:** We collect the minimum data necessary to operate the service.
Ghost and stranger visitor data is anonymised (hashed identifiers).
Personal data is never sold or shared with third parties.
All storage uses AES-256-GCM encryption at rest; TLS 1.3 in transit.

---

## 5. Data Storage ("Cloud Memory")

When you interact with the neohiro assistant, the system may store:

- **Conversation context** — to maintain memory across sessions
- **Preference profiles** — to personalise responses
- **Credential metadata** — encrypted vault entries (AES-256-GCM, age-encrypted)

You can request deletion of your data at any time.
See the **Right to Erasure** section of [/privacy](/privacy/).

---

## 6. Consent & Onboarding

On first interaction, you will be shown a **consent notice**:

> *"Your information is safely stored as cloud memory to help us learn more about you and improve your experience. Do not use this service if you decline. [Read our Privacy Policy](/privacy/) | [Terms of Service](/tos/)*"

By continuing, you consent to this storage.
You may withdraw consent at any time by requesting data deletion.

---

## 7. Service Availability

The neohiro infrastructure is provided **as-is**. While we run self-healing
cadence loops (Heart) and organ-failure monitoring (monitor.sh), we do not
guarantee uptime. Organ-failure events are logged and escalated automatically.

If you deploy this infrastructure, **you are responsible** for maintaining
your own deployment, monitoring, and backups.

---

## 8. Third-Party Services

The neohiro stack integrates with:

- GitHub (OAuth, API, Actions)
- WhatsApp (via Baileys bridge)
- OpenAI / Claude / Gemini (LLM inference)
- Tailscale (zero-config VPN)
- External threat intelligence feeds (optional)

Each third-party service is governed by its own Terms of Service and Privacy Policy.
We are not responsible for the practices of third parties.

---

## 9. Intellectual Property

The **FrenzyPenguin Media / neohiro additions** to this stack are licensed
under **GNU GPL-3.0**. See the [LICENSE](https://github.com/neohiro/neohiro.github.io/blob/main/LICENSE) for details.

Third-party components retain their original licenses.

---

## 10. Limitation of Liability

To the maximum extent permitted by law, **FrenzyPenguin Media** is not liable
for any direct, indirect, incidental, special, or consequential damages arising
from your use of this infrastructure.

**No warranty** is provided. The software is distributed **WITHOUT WARRANTY OF
ANY KIND**, express or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose, and non-infringement.

---

## 11. Termination

We may suspend or terminate access to any service at any time for:

- Violation of these Terms
- Abuse, harassment, or security threats
- Legal obligations requiring disclosure or removal

You may terminate your own data storage at any time by requesting deletion.

---

## 12. Changes to These Terms

We may update these Terms to reflect changes in our infrastructure, legal
requirements, or business practices. Changes will be posted on this page
with an updated effective date. Continued use constitutes acceptance.

---

## 13. Contact

For questions about these Terms:
- Email: `contact@frenzypenguin.media`
- GitHub: [https://github.com/neohiro](https://github.com/neohiro)
- Repository: `neohiro/wingman-hub` (Private — contact via email)

---

*Last reviewed: 2026-01-01*
