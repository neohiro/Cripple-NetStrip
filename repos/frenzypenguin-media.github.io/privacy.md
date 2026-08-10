---
layout: default
title: Privacy Policy
description: "Privacy Policy — neohiro infrastructure"
permalink: /privacy/
---

# Privacy Policy

**Effective: January 1, 2026**  
**Operator: FrenzyPenguin Media** (`contact@frenzypenguin.media`)  
**Jurisdiction: Belgium / European Union (GDPR-aligned)**

---

## 1. Overview

This Privacy Policy describes how **FrenzyPenguin Media** ("we", "us", "the Operator")
processes personal data, communications, and digital artifacts through the neohiro
infrastructure (collectively "the System"). The System includes Brain, Heart, Mouth,
Voicemail, userdata, and all associated tools.

The System is operated exclusively by FrenzyPenguin Media. There is no third-party
data broker relationship.

---

## 2. The data we process

### 2.1 Conversation and message data (only when you interact)

When you send a message, voice note, or document to the assistant:

| What | Why | How long |
|---|---|---|
| Message text | To respond and learn preferences | Until you delete it |
| Voice transcriptions | To respond | Until you delete it |
| Display names / handles | To greet you correctly | Until you delete it |
| Phone numbers / device IDs | To route your messages | Until you delete it |
| Delivery receipts | To confirm delivery | 30 days |

**No message content is ever sold or shared with third parties.**

### 2.2 Authorisation and identity

When you authenticate (GitHub OAuth, voice PIN, etc.):

- **GitHub username** — stored hashed (sha256 truncated), used to identify your account
- **Email address** — optional, stored only if you provide it
- **IP address** — hashed immediately (sha256), never stored raw
- **GeoIP country** — derived from IP, used only for anomaly detection
- **Authentication history** — for security audit, kept for 12 months

### 2.3 Ghost and stranger visitor data

Visitors who have not authenticated are treated as **ghosts** or **strangers**:

- **Ghosts** — never contacted, hashed identifiers, observations are TTL'd (90 days)
- **Strangers** — GeoIP-only, may receive automated triage response, hashed identifiers
- **Raw IPs are never persisted** in ghost or stranger records
- Observations are public-data only (mentions, third-party handles)

### 2.4 Hearsay and relations

The hearsay cache stores **derived attributes** about entities that have a
double-confirmed relation with you. Only low-bandwidth data is included:

- `role`, `last_seen_bucket`, `social_boost_band`, `activity_bucket`,
  `presence`, `mutual_count`, `tag_set`, `public_credit_count`

**No PII** is stored in the hearsay cache — no emails, IPs, addresses, or full names.

### 2.5 Cloud memory and preference profiles

When you opt in to cloud memory, we store:

- **Conversation summaries** — to maintain context across sessions
- **Preference profiles** — dietary, scheduling, project, contact preferences
- **Encrypted vault entries** — credentials, payment cards, API keys (AES-256-GCM)
- **Contact relations** — your family, friends, co-admins, teams (with their consent)

**All vault entries are stored encrypted with age.**
**You may delete any item at any time via the vault management interface.**

---

## 3. Legal basis for processing

We process your personal data on the following legal bases under GDPR:

- **Contract** — when you sign up and use the service
- **Consent** — when you opt in to cloud memory or specific features
- **Legitimate interest** — fraud prevention, security monitoring
- **Legal obligation** — when required by law

---

## 4. Cryptographic security

### 4.1 Encryption at rest

| Storage | Method | Key length | Status |
|---|---|---|---|
| Cold vault (credentials) | AES-256-GCM | 256-bit | Post-quantum safe |
| Hot memory (conversations) | AES-256-GCM | 256-bit | Standard |
| age-encrypted secrets | age (X25519 + scrypt) | 256-bit | Post-quantum safe |
| godadmin vault | age (multi-recipient) | 256-bit | Post-quantum safe |

**Unique IVs** — every encryption uses a fresh 96-bit random IV.
**Authentication tags** — every encrypted blob is verified before decryption.

### 4.2 Encryption in transit

- **TLS 1.3** — for all LLM API and database traffic
- **Forward secrecy** — X25519 ephemeral keys
- **HSTS** — for all public endpoints

---

## 5. Administrative access and oversight

> [!IMPORTANT]
> **Owner oversight notice:**
> The Primary Administrator (God Admin / Owner) retains full administrative
> access to all underlying databases, conversation transcripts, error logs, and
> automated triage reports. This access is for system security, operational
> integrity, fraud prevention, and quality improvement.

Day-to-day user data is **cryptographically and logically isolated** between
individual user accounts. However, **complete privacy from the system operator
is not guaranteed or implied** by the use of this service.

---

## 6. Stranger contact and triage

Incoming messages from unrecognized numbers or identifiers undergo automated triage:

1. **Automated reception** — the assistant delivers a standard professional auto-reply
2. **OSINT verification** — best-effort, open-source intelligence on the contact
3. **Admin escalation** — a structured triage summary is sent to the God Admin

Unrecognized contacts are **never** granted administrative access, memory
inspection, or repository tools.

---

## 7. Data retention

| Data type | Retention | Deletion |
|---|---|---|
| Conversation history | Until you delete | Self-service or request |
| Vault entries | Until you delete | Self-service or request |
| Ghost observations | 90 days (auto-pruned) | Automatic |
| Authentication history | 12 months | Automatic |
| Audit logs (operational) | 24 months | Automatic |
| Anonymised analytics | Aggregated, no identifiers | N/A |

---

## 8. Right to erasure

You have the right to delete your data at any time:

- **Self-service** — use the vault management interface to delete entries
- **Request** — email `contact@frenzypenguin.media` with your account ID
- **Response time** — within 30 days, typically 7 days
- **Scope** — we delete all data linked to your account, except:
  - Aggregated, non-identifying analytics
  - Legal compliance records (where required)

---

## 9. Data sharing

**We do not sell your data. We do not share your data with third parties for marketing.**

Limited sharing only occurs:

- **With your explicit consent** (e.g., integration with third-party tools you configure)
- **To comply with legal obligations** (court orders, lawful requests)
- **To protect the System** (abuse prevention, fraud detection)
- **With service providers** (LLM inference, cloud hosting) who are contractually bound

---

## 10. International transfers

The neohiro infrastructure is operated in the European Union.
If data is transferred outside the EU, we use:

- **Standard Contractual Clauses** (SCC) approved by the European Commission
- **Adequacy decisions** — only to countries with equivalent data protection
- **Encryption** — all data is encrypted in transit and at rest

---

## 11. Children's privacy

The System is **not intended for users under 16 years of age**.
We do not knowingly collect data from children.
If we learn we have collected data from a child, we will delete it promptly.

---

## 12. Your rights (GDPR)

If you are in the EU, you have the right to:

- **Access** — request a copy of your data
- **Rectification** — correct inaccurate data
- **Erasure** — request deletion
- **Restrict processing** — limit how we use your data
- **Data portability** — receive your data in a machine-readable format
- **Object** — to certain types of processing
- **Withdraw consent** — at any time, without affecting prior processing

To exercise any of these rights, contact `contact@frenzypenguin.media`.

---

## 13. Organ-failure diagnostics

We use medical analogies throughout the System. This is for **readability and
alert fatigue reduction**, not because we are insensitive to medical issues.
When a component fails, we describe it as **organ failure**. The recovery process
is **regeneration**. The abuse filter is the **immune system**. The doctor is
**paramedic services**. The GH Actions fallback is the **sepsis protocol**.

This is a deliberate UX choice so engineers and operators can quickly
diagnose system state without jargon fatigue.

---

## 14. Changes to this policy

We may update this Privacy Policy to reflect changes in our infrastructure,
legal requirements, or business practices. Changes will be posted on this page
with an updated effective date. We will notify you via the assistant when
material changes occur.

---

## 15. Contact

For questions about this Privacy Policy or your data:

- **Email:** `contact@frenzypenguin.media`
- **GitHub:** [https://github.com/neohiro](https://github.com/neohiro)
- **Mailing address:** FrenzyPenguin Media, Belgium

---

*Last reviewed: 2026-01-01*
