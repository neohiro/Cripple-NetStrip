/**
 * auto-resume.js — resilience + unattended-autonomy plugin for OpenCode.
 * Install machine-wide:  ~/.config/opencode/plugins/auto-resume.js
 * (Do NOT also keep a project-level copy: global + project copies would both
 *  load and double-fire every hook.)
 *
 * ══════════════════════════════════════════════════════════════════
 *  SUBSYSTEM 1 — RECOVERY (always on while plugin enabled)
 * ══════════════════════════════════════════════════════════════════
 * Keeps a turn alive whenever OpenCode's own internal retry gives up:
 *   • network/transport failures (ECONNRESET, fetch failed, DNS, TLS, ...)
 *   • provider outages (5xx, 529 overloaded, gateway errors)
 *   • request timeouts (408) — exponential backoff + jitter, honors Retry-After
 *   • truncated output (MessageOutputLengthError) → seamless continue nudge
 *   • context-window overflow → triggers compaction, resumes afterwards
 *   • empty responses → re-nudge
 *   • stalled streams (busy w/o events) → abort + restart (skips pending perms,
 *     extended grace while a long tool legitimately runs)
 *   • internal retry loops that never end (huge provider Retry-After values)
 *     → taken over: aborted and resumed by the plugin
 *   • server/machine crashes → on startup, recently-active interrupted
 *     sessions are re-animated automatically
 *   • subagent/child sessions are left to their parent orchestrator
 *   • user aborts are always respected; auth errors surfaced, never hammered
 *
 * ══════════════════════════════════════════════════════════════════
 *  SUBSYSTEM 2 — MODEL ROTATION (no user input required)
 * ══════════════════════════════════════════════════════════════════
 * On free-tier/quota exhaustion or repeated rate limits of a model:
 *   • puts the exhausted model on a cooldown (default 60 min)
 *   • picks the best available alternative automatically:
 *       1. OPENCODE_RESUME_FALLBACK_MODELS preferred chain (env)
 *       2. sibling models from the same provider
 *       3. models from other installed providers
 *     Candidates are ranked by capability tier — Max/Ultra/Opus/Pro/High
 *     variants win whenever they exist; mini/nano/lite/flash variants lose.
 *     (non-chat models like embeddings/TTS/image are always filtered out)
 *   • continues the exact same session/conversation on the new model
 *   • ALSO rotates on persistent model-specific failures: repeated network
 *     errors / endpoint unavailability / 5xx waves on one model move the
 *     session to a different model (without cooldown-penalizing the old one,
 *     since outages are often provider-side and temporary)
 *
 * ══════════════════════════════════════════════════════════════════
 *  SUBSYSTEM 3 — PERMISSION AUTOPILOT (unattended operation)
 * ══════════════════════════════════════════════════════════════════
 * Auto-answers permission prompts so the agent never blocks while you're away:
 *   • safe mode (default): edits/web-fetches approved; shell commands approved
 *     UNLESS they match a dangerous-pattern blocklist (rm -rf, force push,
 *     disk format, registry edits, pipe-to-shell ...) — matched ones are
 *     REJECTED so the agent adapts instead of hanging
 *   • unknown permission types are left for the user in safe mode
 *
 * ══════════════════════════════════════════════════════════════════
 *  SUBSYSTEM 4 — TASK DRIVER (walk-away automation)
 * ══════════════════════════════════════════════════════════════════
 * Lets you hand a big task to OpenCode and leave:
 *   • TODO DRIVE: session goes idle with unfinished todos → nudges it to
 *     continue (spin-detection stops it if nothing progresses)
 *   • DEBUG NUDGE: 3 consecutive failed tool calls → tells the model to stop
 *     repeating the failing approach and diagnose the root cause first
 *   • AUTONOMY DIRECTIVE: every injected prompt instructs the model to make
 *     its own decisions, never wait for confirmation, document assumptions
 *   • AUTO-PROCEED: if the agent ends its turn by asking a question
 *     ("Should I proceed...?"), it answers itself and continues (capped)
 *   • WRAP-UP: when the todo list completes → asks once for concrete
 *     improvement proposals (listed, not implemented) + success toast
 *   • BEYOND EXPECTATIONS: before wrapping up, runs a self-critique pass —
 *     the model reviews its own work for correctness/perf/security/robustness
 *     improvements and implements the safe ones (capped number of cycles)
 *
 * Safety rails: per-task resume-chain cap, shared autopilot-nudge cap, task
 * wall-clock budget, spin detection, circuit breaker with cool-down,
 * incident-signature dedupe, idle-status check before every injection.
 * All injected user messages are tagged "[auto-resume]" for visibility.
 *
 * ══════════════════════════════════════════════════════════════════
 *  CONFIGURATION (env vars, all optional)
 * ══════════════════════════════════════════════════════════════════
 *  OPENCODE_RESUME_ENABLED               master switch              (true)
 *  OPENCODE_RESUME_MAX_CHAIN             recovery resumes per task  (6)
 *  OPENCODE_RESUME_BASE_DELAY_MS         backoff base               (5000)
 *  OPENCODE_RESUME_MAX_DELAY_MS          backoff cap                (120000)
 *  OPENCODE_RESUME_RATE_LIMIT_BASE_MS    429 backoff base           (20000)
 *  OPENCODE_RESUME_OUTPUT_LENGTH_MAX     truncation nudges          (3)
 *  OPENCODE_RESUME_NUDGE_DELAY_MS        continue-nudge delay       (1500)
 *  OPENCODE_RESUME_STALL_TIMEOUT_MS      busy-silence => stalled    (240000)
 *  OPENCODE_RESUME_WATCHDOG_MS           stall check interval       (10000)
 *  OPENCODE_RESUME_RUNNING_TOOL_FACTOR   grace multiplier while a
 *                                        tool is running            (4)
 *  OPENCODE_RESUME_RETRY_TAKEOVER_MS     stuck-in-core-retry limit  (900000)
 *  OPENCODE_RESUME_RETRY_FUTURE_CAP_MS   absurd next-retry distance (600000)
 *  OPENCODE_RESUME_REANIMATE             revive crashed sessions    (true)
 *  OPENCODE_RESUME_REANIMATE_WINDOW_MS   max age for revival        (600000)
 *  OPENCODE_RESUME_BREAKER_THRESHOLD     failures before breaker    (6)
 *  OPENCODE_RESUME_BREAKER_WINDOW_MS     breaker rolling window     (900000)
 *  OPENCODE_RESUME_BREAKER_COOLDOWN_MS   breaker cool-down          (300000)
 *  OPENCODE_RESUME_COMPACT_ON_OVERFLOW   summarize then resume      (true)
 *  OPENCODE_RESUME_TOAST_THROTTLE_MS     min gap between toasts     (3000)
 *  OPENCODE_RESUME_SWITCH_ON_QUOTA       rotate model on free-tier  (true)
 *  OPENCODE_RESUME_SWITCH_ON_RATELIMIT   rotate after N 429s        (true)
 *  OPENCODE_RESUME_SWITCH_ON_FAILURES    rotate after persistent
 *                                        network/5xx failures       (true)
 *  OPENCODE_RESUME_RL_SWITCH_AFTER       429s before rotating       (2)
 *  OPENCODE_RESUME_ROTATE_AFTER_FAILURES failed rounds before
 *                                        rotating away              (3)
 *  OPENCODE_RESUME_MAX_ROTATIONS         model rotations per task   (3)
 *  OPENCODE_RESUME_MODEL_COOLDOWN_MS     exhausted-model pause      (3600000)
 *  OPENCODE_RESUME_FALLBACK_MODELS       preferred chain, e.g.
 *                                        "anthropic/claude-sonnet-4,openai/gpt-5,cerebras/llama3.3-70b"
 *  OPENCODE_RESUME_AUTONOMY              master switch subsystem 3+4(true)
 *  OPENCODE_AUTOPILOT_PERMISSIONS        auto-answer permissions    (true)
 *  OPENCODE_AUTOPILOT_PERMISSION_MODE    safe | all                 (safe)
 *  OPENCODE_AUTOPILOT_EXTRA_DENY         comma-separated extra deny regexes
 *  OPENCODE_AUTOPILOT_TODO_DRIVE         continue unfinished todos  (true)
 *  OPENCODE_AUTOPILOT_DEBUG_NUDGE        diagnose after tool errors (true)
 *  OPENCODE_AUTOPILOT_PROPOSALS          wrap-up proposals message  (true)
 *  OPENCODE_AUTOPILOT_PROCEED            answer the agent's own
 *                                        questions and continue     (true)
 *  OPENCODE_AUTOPILOT_MAX_PROCEEDS       self-answers per task      (3)
 *  OPENCODE_AUTOPILOT_IMPROVE            self-improvement pass      (true)
 *  OPENCODE_AUTOPILOT_IMPROVE_CYCLES     max improvement cycles     (2)
 *  OPENCODE_AUTOPILOT_MAX_NUDGES         max self-driven nudges/task(25)
 *  OPENCODE_AUTOPILOT_BUDGET_MS          wall-clock budget per task (28800000 = 8h, 0=off)
 */

const DEFAULTS = {
  enabled: true,
  maxChain: 6,
  baseDelayMs: 5_000,
  maxDelayMs: 120_000,
  rateLimitBaseMs: 20_000,
  outputLengthMax: 3,
  nudgeDelayMs: 1_500,
  stallTimeoutMs: 240_000,
  watchdogMs: 10_000,
  runningToolFactor: 4,
  retryTakeoverMs: 900_000,
  retryFutureCapMs: 600_000,
  reanimate: true,
  reanimateWindowMs: 600_000,
  breakerThreshold: 6,
  breakerWindowMs: 900_000,
  breakerCooldownMs: 300_000,
  compactOnOverflow: true,
  toastThrottleMs: 3_000,
  switchOnQuota: true,
  switchOnRateLimit: true,
  switchOnFailures: true,
  rlSwitchAfter: 2,
  rotateAfterFailures: 3,
  maxRotations: 3,
  modelCooldownMs: 3_600_000,
  fallbackModels: "",
  autonomy: true,
  permissions: true,
  permissionMode: "safe",
  extraDeny: "",
  todoDrive: true,
  debugNudge: true,
  proposals: true,
  proceedOnAsk: true,
  maxProceeds: 3,
  improveLoop: true,
  improveCycles: 2,
  maxNudges: 25,
  budgetMs: 28_800_000,
}

const RESUME_TAG = "[auto-resume]"

const AUTONOMY_DIRECTIVE =
  " You are running unattended: make reasonable decisions yourself, never wait for confirmation or ask questions, prefer completing the task over asking, choose sensible defaults, verify your own work, and document any assumptions you made."

const PROMPTS = {
  resume: (auto) =>
    `${RESUME_TAG} The previous attempt was interrupted by a transient infrastructure error (network outage, provider error, rate limit, or timeout). Continue the interrupted task from exactly where you left off. Do not apologize, do not repeat completed work, do not summarize unless asked.` +
    (auto ? AUTONOMY_DIRECTIVE : ""),
  truncated: (auto) =>
    `${RESUME_TAG} Your previous reply hit the maximum output length and was cut off mid-response. Continue seamlessly from the exact point where you stopped, without repeating any earlier content.` +
    (auto ? AUTONOMY_DIRECTIVE : ""),
  empty: (auto) =>
    `${RESUME_TAG} Your previous response arrived empty, likely due to a transient provider issue. Please produce your answer to the original request now.` +
    (auto ? AUTONOMY_DIRECTIVE : ""),
  todos: () =>
    `${RESUME_TAG} This session went idle while the todo list still has unfinished items. Continue working through them autonomously now, one by one, marking each completed as you go.`,
  proceed: () =>
    `${RESUME_TAG} Proceed autonomously with exactly what you just proposed or asked about — the answer is yes. Do not ask again; decide and continue.` +
    AUTONOMY_DIRECTIVE,
  keepGoing: () =>
    `${RESUME_TAG} You ended your reply indicating there is still work to do ("continue", "finalize", etc.) but the turn stopped. Pick up exactly where you left off right now and finish it. Do not restate what is already done.` +
    AUTONOMY_DIRECTIVE,
  debug: () =>
    `${RESUME_TAG} The last several tool calls failed repeatedly. Stop repeating the same failing approach. Diagnose the actual root cause first (read the full error output, inspect relevant files/state), form a hypothesis, then apply a targeted fix.`,
  improve: (cycle, total) =>
    `${RESUME_TAG} Self-improvement pass ${cycle}/${total}: critically review ALL work produced in this session. Hunt for concrete improvements in correctness, performance, security, robustness, and readability — edge cases, missing error handling, stale docs or comments, gaps in test coverage, inefficient hot spots. Directly implement every improvement you are confident about and validate it (run the relevant builds/tests/linters). Explicitly skip anything ambiguous or risky and note why in one line. Do NOT introduce new features.` +
    AUTONOMY_DIRECTIVE,
  propose: () =>
    `${RESUME_TAG} The todo list is fully complete. Do NOT implement anything further. Instead reply with a short wrap-up: what was accomplished, plus up to 3 concrete follow-up improvement proposals as bullet points.`,
}

const NETWORK_PATTERNS = [
  "fetch failed", "econnreset", "econnrefused", "econnaborted", "etimedout",
  "esockettimedout", "socket hang up", "connection refused", "connection reset",
  "connection closed", "connection terminated", "other side closed",
  "premature close", "terminated", "stream ended unexpectedly", "network",
  "enotfound", "eai_again", "dns", "tls", "ssl", "handshake", "gateway",
  "overloaded_error", "overloaded", "bad gateway", "service unavailable",
  "internal server error",
]

const OVERFLOW_PATTERNS = [
  "context length", "context window", "too many tokens", "token limit",
  "maximum context", "input length exceeds", "input tokens exceed",
  "prompt is too long", "prompt too long", "reduce the length",
  "exceed the maximum number of tokens",
]

const QUOTA_PATTERNS = [
  "free usage exceeded", "free tier", "free-tier", "quota", "billing",
  "payment required", "credit balance", "insufficient", "usage limit",
  "limit reached", "upgrade to go", "subscribe to go", "exceeded your",
]

/** Model ids that look like non-chat endpoints and must never receive prompts. */
const NON_CHAT_PATTERN = /embed|whisper|tts|speech|transcri|image|imagen|dall|moderation|guard|rerank|vision-only|caption/i

/** Capability-tier hints used to prefer the strongest variant of a family.
 *  Word-boundary matched against the model id, case-insensitive. */
const TIER_BONUS = [
  [/\bmax(imum)?\b/i, 60], [/\bultra\b/i, 60], [/\bopus\b/i, 55],
  [/\bpro\b/i, 45], [/\bhigh\b/i, 45], [/\bpremium\b/i, 40],
  [/\badvanced?\b/i, 35], [/\b(xl|xxl)\b/i, 30], [/\blarge(r)?\b/i, 25],
  [/\b(sonnet|gpt-?[5-9]|o[1-9])\b/i, 20], [/\b(200b|405b|671b)\b/i, 20],
  [/\b(70b|72b|80b|120b|140b|235b)\b/i, 15], [/\bthinking\b/i, 10],
]
const TIER_PENALTY = [
  [/\bmini\b/i, -50], [/\bnano\b/i, -50], [/\btiny\b/i, -45],
  [/\bsmall(est)?\b/i, -40], [/\blite\b/i, -40], [/\bflash\b/i, -35],
  [/\binstant\b/i, -35], [/\bexpress\b/i, -35], [/\bhaiku\b/i, -30],
  [/\bfast(est)?\b/i, -25], [/\bbasic\b/i, -25], [/\blean\b/i, -20],
]

/** Turn-ending question markers: the agent stopped to ask instead of doing. */
const QUESTION_PATTERNS = [
  /\bshall i\b/i, /\bshould i\b/i, /\bwould you like me\b/i,
  /\bdo you want me to\b/i, /\bwant me to\b/i, /\bcan i (proceed|continue|start|begin|go ahead)\b/i,
  /\bshould we\b/i, /\blet me know (if|when|whether)\b/i,
  /\bawait(ing)? (your|further) (confirmation|instructions|approval|input)\b/i,
  /\bwaiting for your\b/i, /\bprompt (me|you) when\b/i,
]

/** Turn-ending continuation stubs: the agent announced more work but stopped
 *  ("Continue to finalize.", "Continuing...", "To be continued.") without a
 *  question mark — so the question detector never fires on these. */
const CONTINUATION_ANYWHERE = [
  /\bcontinue to finalize\b/i,
  /\bto be continued\b/i,
  /\bwill continue\b/i,
  /\bcontinu(e|ing) (in the next|with the next|shortly|below)\b/i,
  /\bmore (to come|coming soon|follows)\b/i,
]
const CONTINUATION_STEM = /^(continue|continuing|resumed?|proceeding|finalizing|finalize|finishing|finishing up|wrapping up|next up|partial(?:ly)? (?:done|complete)|incomplete)\b/i

/** A short closing line announcing unfinished work. */
const looksLikeContinuationStub = (text) => {
  const t = String(text ?? "").trim()
  if (!t || t.length > 250) return false
  return CONTINUATION_STEM.test(t) || CONTINUATION_ANYWHERE.some((re) => re.test(t))
}

/** Unambiguous phrases count even inside longer replies. */
const looksLikeContinuationLong = (text) => {
  const t = String(text ?? "").trim()
  if (!t) return false
  return CONTINUATION_ANYWHERE.some((re) => re.test(t))
}

const tierScore = (modelID) => {
  let score = 0
  for (const [re, pts] of TIER_BONUS) if (re.test(modelID)) score += pts
  for (const [re, pts] of TIER_PENALTY) if (re.test(modelID)) score += pts
  return score
}

/** Shell fragments considered too dangerous to auto-approve in safe mode.
 *  Plain case-insensitive substrings by default; "re:<body>" opts into regex
 *  (kept off by default after ':(){' / '| sudo sh' style footguns). */
const DANGEROUS_PATTERNS = [
  "rm -rf", "rm -fr", "rm -r /", "rmdir /s", "del /s", "del /f", "erase /f",
  "format ", "mkfs", "dd if=", "fork bomb", ":(){", "shutdown", "reboot",
  "halt ", "git push --force", "git push -f", "git reset --hard",
  "git clean -fd", "git clean -df", "drop database", "drop table",
  "truncate table", "chmod -r 777", "reg add hkey", "reg delete",
  "remove-item -recurse", "remove-item -force", "curl | sh", "curl | bash",
  "curl|sh", "curl|bash", "wget | sh", "wget | bash", "wget|sh",
  "| sudo sh", "|sudo sh", "--no-verify",
  "> /dev/sda", "diskpart", "cipher /w", "vssadmin delete",
]

function num(name, fallback) {
  const v = Number(process.env[name])
  return Number.isFinite(v) && v >= 0 ? v : fallback
}
function str(name, fallback) {
  const v = process.env[name]
  return v === undefined || v === "" ? fallback : v
}
function bool(name, fallback) {
  const v = process.env[name]
  if (v === undefined || v === "") return fallback
  return !["0", "false", "no", "off"].includes(v.toLowerCase())
}

function loadConfig() {
  return {
    enabled: bool("OPENCODE_RESUME_ENABLED", DEFAULTS.enabled),
    maxChain: num("OPENCODE_RESUME_MAX_CHAIN", DEFAULTS.maxChain),
    baseDelayMs: num("OPENCODE_RESUME_BASE_DELAY_MS", DEFAULTS.baseDelayMs),
    maxDelayMs: num("OPENCODE_RESUME_MAX_DELAY_MS", DEFAULTS.maxDelayMs),
    rateLimitBaseMs: num("OPENCODE_RESUME_RATE_LIMIT_BASE_MS", DEFAULTS.rateLimitBaseMs),
    outputLengthMax: num("OPENCODE_RESUME_OUTPUT_LENGTH_MAX", DEFAULTS.outputLengthMax),
    nudgeDelayMs: num("OPENCODE_RESUME_NUDGE_DELAY_MS", DEFAULTS.nudgeDelayMs),
    stallTimeoutMs: num("OPENCODE_RESUME_STALL_TIMEOUT_MS", DEFAULTS.stallTimeoutMs),
    watchdogMs: num("OPENCODE_RESUME_WATCHDOG_MS", DEFAULTS.watchdogMs),
    runningToolFactor: Math.max(1, num("OPENCODE_RESUME_RUNNING_TOOL_FACTOR", DEFAULTS.runningToolFactor)),
    retryTakeoverMs: num("OPENCODE_RESUME_RETRY_TAKEOVER_MS", DEFAULTS.retryTakeoverMs),
    retryFutureCapMs: num("OPENCODE_RESUME_RETRY_FUTURE_CAP_MS", DEFAULTS.retryFutureCapMs),
    reanimate: bool("OPENCODE_RESUME_REANIMATE", DEFAULTS.reanimate),
    reanimateWindowMs: num("OPENCODE_RESUME_REANIMATE_WINDOW_MS", DEFAULTS.reanimateWindowMs),
    breakerThreshold: num("OPENCODE_RESUME_BREAKER_THRESHOLD", DEFAULTS.breakerThreshold),
    breakerWindowMs: num("OPENCODE_RESUME_BREAKER_WINDOW_MS", DEFAULTS.breakerWindowMs),
    breakerCooldownMs: num("OPENCODE_RESUME_BREAKER_COOLDOWN_MS", DEFAULTS.breakerCooldownMs),
    compactOnOverflow: bool("OPENCODE_RESUME_COMPACT_ON_OVERFLOW", DEFAULTS.compactOnOverflow),
    toastThrottleMs: num("OPENCODE_RESUME_TOAST_THROTTLE_MS", DEFAULTS.toastThrottleMs),
    switchOnQuota: bool("OPENCODE_RESUME_SWITCH_ON_QUOTA", DEFAULTS.switchOnQuota),
    switchOnRateLimit: bool("OPENCODE_RESUME_SWITCH_ON_RATELIMIT", DEFAULTS.switchOnRateLimit),
    switchOnFailures: bool("OPENCODE_RESUME_SWITCH_ON_FAILURES", DEFAULTS.switchOnFailures),
    rlSwitchAfter: Math.max(1, num("OPENCODE_RESUME_RL_SWITCH_AFTER", DEFAULTS.rlSwitchAfter)),
    rotateAfterFailures: Math.max(1, num("OPENCODE_RESUME_ROTATE_AFTER_FAILURES", DEFAULTS.rotateAfterFailures)),
    maxRotations: num("OPENCODE_RESUME_MAX_ROTATIONS", DEFAULTS.maxRotations),
    modelCooldownMs: num("OPENCODE_RESUME_MODEL_COOLDOWN_MS", DEFAULTS.modelCooldownMs),
    fallbackModels: str("OPENCODE_RESUME_FALLBACK_MODELS", DEFAULTS.fallbackModels),
    autonomy: bool("OPENCODE_RESUME_AUTONOMY", DEFAULTS.autonomy),
    permissions: bool("OPENCODE_AUTOPILOT_PERMISSIONS", DEFAULTS.permissions),
    permissionMode: str("OPENCODE_AUTOPILOT_PERMISSION_MODE", DEFAULTS.permissionMode).toLowerCase(),
    extraDeny: str("OPENCODE_AUTOPILOT_EXTRA_DENY", DEFAULTS.extraDeny),
    todoDrive: bool("OPENCODE_AUTOPILOT_TODO_DRIVE", DEFAULTS.todoDrive),
    debugNudge: bool("OPENCODE_AUTOPILOT_DEBUG_NUDGE", DEFAULTS.debugNudge),
    proposals: bool("OPENCODE_AUTOPILOT_PROPOSALS", DEFAULTS.proposals),
    proceedOnAsk: bool("OPENCODE_AUTOPILOT_PROCEED", DEFAULTS.proceedOnAsk),
    maxProceeds: num("OPENCODE_AUTOPILOT_MAX_PROCEEDS", DEFAULTS.maxProceeds),
    improveLoop: bool("OPENCODE_AUTOPILOT_IMPROVE", DEFAULTS.improveLoop),
    improveCycles: num("OPENCODE_AUTOPILOT_IMPROVE_CYCLES", DEFAULTS.improveCycles),
    maxNudges: num("OPENCODE_AUTOPILOT_MAX_NUDGES", DEFAULTS.maxNudges),
    budgetMs: num("OPENCODE_AUTOPILOT_BUDGET_MS", DEFAULTS.budgetMs),
  }
}

const matchesAny = (haystack, patterns) => {
  if (!haystack) return false
  const lower = String(haystack).toLowerCase()
  return patterns.some((p) => lower.includes(p))
}
const jitter = (ms) => Math.round(ms + ms * 0.25 * (Math.random() * 2 - 1))

export const AutoResumePlugin = async ({ client }) => {
  const cfg = loadConfig()

  const sessions = new Map() // sessionID -> state
  const permissionPending = new Map() // sessionID -> ts
  const modelCooldown = new Map() // "provider/model" -> untilTs
  const timers = new Map()
  const breakerFailures = []
  let breakerOpenUntil = 0
  let breakerToasted = false
  let lastToastAt = 0
  let catalogCache = null
  let catalogFetchedAt = 0

  const state = (id) => {
    let s = sessions.get(id)
    if (!s) {
      s = {
        status: "unknown", lastActivity: Date.now(),
        lastErrorAt: 0, lastErrorSig: null, lastErrorName: null,
        chain: 0, continueCount: 0, stallResumes: 0, emptyNudges: 0,
        compactAttempted: false, awaitingCompactionSince: 0,
        pendingResume: false, lastResumeAt: 0, lastInjectAt: 0,
        lastModel: null, currentModel: null, originalModel: null,
        rlStreak: 0, failStreak: 0, rotations: 0,
        todos: [], nudges: 0, driveCount: 0, staleDrives: -1,
        lastDriveCompleted: -1, proposalSent: false, taskStartAt: 0,
        improveDone: 0, proceedCount: 0,
        toolErrs: 0, debugArmed: false, toolRunning: false,
        lastTurnHadText: false,
        retryEnteredAt: 0, retryNext: 0, child: false, reanimated: false,
      }
      sessions.set(id, s)
    }
    return s
  }

  /** Fresh-task boundary detection: any REAL (human or injected-but-new) user turn. */
  const resetTaskScope = (s, keepTimers = true) => {
    Object.assign(s, {
      chain: 0, continueCount: 0, compactAttempted: false,
      rlStreak: 0, failStreak: 0, rotations: 0,
      nudges: 0, driveCount: 0, staleDrives: -1,
      lastDriveCompleted: -1, proposalSent: false, improveDone: 0,
      proceedCount: 0, taskStartAt: Date.now(), toolErrs: 0,
      debugArmed: false, retryEnteredAt: 0, retryNext: 0,
      lastTurnHadText: false,
      lastErrorName: null, lastErrorSig: null,
    })
    if (!keepTimers) s.stallResumes = 0
  }

  const detach = (promise, label) =>
    Promise.resolve().then(promise).catch(
      (err) => console.error(`${RESUME_TAG} ${label} failed:`, err?.message ?? err))

  const log = (level, message, extra) =>
    detach(() => client.app.log({ body: { service: "auto-resume", level, message, extra } }), "app.log")

  const toast = (message, variant = "warning") => {
    const nowMs = Date.now()
    if (cfg.toastThrottleMs > 0 && nowMs - lastToastAt < cfg.toastThrottleMs) return
    lastToastAt = nowMs
    detach(() => client.tui.showToast({ body: { message, variant } }), "toast")
  }

  // ── circuit breaker ────────────────────────────────────────────────
  const breakerOpen = () => Date.now() < breakerOpenUntil
  const noteResumeFailure = () => {
    const nowMs = Date.now()
    breakerFailures.push(nowMs)
    while (breakerFailures.length && nowMs - breakerFailures[0] > cfg.breakerWindowMs) breakerFailures.shift()
    if (breakerFailures.length >= cfg.breakerThreshold) {
      breakerOpenUntil = nowMs + cfg.breakerCooldownMs
      breakerFailures.length = 0
      log("warn", "circuit breaker opened", { cooldownMs: cfg.breakerCooldownMs })
      toast(`${RESUME_TAG} Repeated failures — pausing auto-recovery for ${Math.round(cfg.breakerCooldownMs / 60_000)} min.`, "error")
    }
  }
  const noteSuccess = () => { breakerFailures.length = 0; breakerOpenUntil = 0; breakerToasted = false }

  // ── classification ─────────────────────────────────────────────────
  const classify = (error) => {
    const name = error?.name
    const data = error?.data ?? {}
    const text = `${data.message ?? ""} ${data.responseBody ?? ""}`
    if (name === "MessageAbortedError") return "abort"
    if (name === "ProviderAuthError") return "auth"
    if (name === "MessageOutputLengthError") return "output_length"
    if (matchesAny(text, QUOTA_PATTERNS)) return "quota"
    if (name === "APIError") {
      const code = data.statusCode
      if (code === 429) return "rate_limit"
      if (code === 408 || code === 409) return "retryable"
      if (typeof code === "number" && code >= 500) return "retryable"
      if (data.isRetryable === true) return "retryable"
      if (matchesAny(text, OVERFLOW_PATTERNS)) return "overflow"
      if (matchesAny(text, NETWORK_PATTERNS)) return "retryable"
      return "fatal"
    }
    if (name === "UnknownError") {
      if (matchesAny(data.message, OVERFLOW_PATTERNS)) return "overflow"
      if (matchesAny(text, NETWORK_PATTERNS)) return "retryable"
      return "fatal"
    }
    return "fatal"
  }

  const retryAfterMs = (error) => {
    const headers = error?.data?.responseHeaders
    if (!headers) return null
    const raw = headers["retry-after"] ??
      Object.entries(headers).find(([k]) => k.toLowerCase() === "retry-after")?.[1]
    if (!raw) return null
    const secs = Number(raw)
    if (Number.isFinite(secs) && secs >= 0) return Math.min(secs * 1_000, 600_000)
    const date = Date.parse(raw)
    if (!Number.isNaN(date)) return Math.min(Math.max(date - Date.now(), 0), 600_000)
    return null
  }

  const backoff = (attempt, base) =>
    Math.min(jitter(base * Math.pow(2, Math.max(attempt - 1, 0))), cfg.maxDelayMs)

  // ── model catalog + rotation ───────────────────────────────────────
  const modelKey = (m) => `${m.providerID}/${m.modelID}`
  const cooling = (key) => (modelCooldown.get(key) ?? 0) > Date.now()

  const getCatalog = async () => {
    if (catalogCache && Date.now() - catalogFetchedAt < 300_000) return catalogCache
    try {
      const res = await client.config.providers()
      const data = res?.data ?? res
      catalogCache = Array.isArray(data?.providers) ? data.providers : []
      catalogFetchedAt = Date.now()
    } catch (err) {
      log("warn", "could not fetch provider catalog", { err: err?.message ?? String(err) })
      catalogCache = catalogCache ?? []
    }
    return catalogCache
  }

  const listChatModels = (providers) => {
    const out = []
    for (const prov of providers) {
      for (const modelID of Object.keys(prov?.models ?? {})) {
        if (NON_CHAT_PATTERN.test(modelID)) continue
        out.push({ providerID: prov.id, modelID })
      }
    }
    return out
  }

  const pickAlternateModel = async (exhausted) => {
    const providers = await getCatalog()
    const all = listChatModels(providers)
    if (!all.length) return null

    const exhaustedKey = exhausted ? modelKey(exhausted) : null
    const eligible = all.filter((m) => {
      const k = modelKey(m)
      if (exhaustedKey && k === exhaustedKey) return false
      if (cooling(k)) return false
      return true
    })
    if (!eligible.length) return null

    // Preferred-chain entries keep absolute priority (explicit user intent);
    // everything else is ranked by capability tier — Max/Ultra/Opus/Pro/High
    // variants beat mini/nano/lite/flash — then by provider proximity.
    const chainSet = new Set(
      cfg.fallbackModels.split(",").map((x) => x.trim()).filter(Boolean),
    )
    const groupOf = (m) => {
      if (chainSet.has(modelKey(m))) return 0
      if (!exhausted || m.providerID === exhausted.providerID) return 1
      return 2
    }
    const ordered = [...eligible].sort((a, b) => {
      const ga = groupOf(a)
      const gb = groupOf(b)
      if (ga !== gb) return ga - gb
      const ta = tierScore(a.modelID)
      const tb = tierScore(b.modelID)
      if (ta !== tb) return tb - ta
      return a.modelID.localeCompare(b.modelID)
    })
    return ordered[0] ?? null
  }

  /**
   * Rotate the session to the best available alternate model.
   * @param {boolean} penalize put the old model on cooldown — yes for quota/
   *   auth/rate-limits; no for generic outages, which are usually temporary.
   */
  const rotateAwayFrom = async (sessionID, reason, penalize = true) => {
    const s = state(sessionID)
    if (s.rotations >= cfg.maxRotations) {
      log("warn", "rotation cap reached", { sessionID, rotations: s.rotations })
      return false
    }
    const exhausted = s.currentModel ?? s.lastModel
    if (exhausted && penalize) {
      modelCooldown.set(modelKey(exhausted), Date.now() + cfg.modelCooldownMs)
      log("info", "model put on cooldown", { sessionID, model: modelKey(exhausted), reason })
    }
    const alt = await pickAlternateModel(exhausted)
    if (!alt) {
      log("warn", "no alternate model available", { sessionID })
      return false
    }
    s.currentModel = { providerID: alt.providerID, modelID: alt.modelID }
    // Fresh lease on the new model — its reliability is unknown so far.
    s.chain = 0
    s.failStreak = 0
    s.rlStreak = 0
    s.rotations += 1
    log("info", "rotated model", {
      sessionID, from: exhausted ? modelKey(exhausted) : null, to: modelKey(alt), reason,
    })
    toast(`${RESUME_TAG}: ${reason} on ${exhausted ? modelKey(exhausted) : "model"} — continuing on ${modelKey(alt)}.`)
    return true
  }

  // ── scheduling / injection ─────────────────────────────────────────
  const schedule = (sessionID, delayMs, plan) => {
    const existing = timers.get(sessionID)
    if (existing) clearTimeout(existing)
    const t = setTimeout(() => {
      timers.delete(sessionID)
      detach(runPlan(sessionID, plan), "runPlan")
    }, delayMs)
    t.unref?.()
    timers.set(sessionID, t)
    log("info", `scheduled "${plan.kind}" in ${delayMs}ms`, { sessionID })
  }

  const autonomousPrompt = (plan) =>
    plan.prompt instanceof Function
      ? plan.prompt(cfg.autonomy)
      : plan.prompt

  /** Child (subagent) sessions belong to their parent orchestrator — never inject. */
  const injectionAllowed = (sessionID) => {
    const s = sessions.get(sessionID)
    if (s?.child) {
      log("info", "skipping injection into subagent session", { sessionID })
      return false
    }
    return true
  }

  const runPlan = async (sessionID, plan) => {
    if (!injectionAllowed(sessionID)) return
    const s = state(sessionID)

    if (plan.kind === "resume") {
      if (breakerOpen()) {
        if (!breakerToasted) {
          breakerToasted = true
          toast(`${RESUME_TAG} Circuit breaker open — auto-recovery suppressed.`, "error")
        }
        return
      }
      s.pendingResume = false
      let status
      try {
        const res = await client.session.status()
        status = (res?.data ?? res)?.[sessionID]?.type
      } catch { status = "unknown" }
      if (status && status !== "idle") {
        schedule(sessionID, 5_000, plan) // core busy/retrying — check again shortly
        return
      }
    }

    const model = s.currentModel ?? s.lastModel
    const body = { parts: [{ type: "text", text: autonomousPrompt(plan) }] }
    if (model) body.model = model

    s.lastInjectAt = Date.now() // mark BEFORE dispatch: user-message event arrives at turn start
    s.lastResumeAt = s.lastInjectAt
    try {
      await client.session.prompt({ path: { id: sessionID }, body })
      log("info", `injected "${plan.kind}"`, { sessionID, model: model ? modelKey(model) : undefined })
    } catch (err) {
      log("error", "resume prompt rejected", { sessionID, err: err?.message ?? String(err) })
      noteResumeFailure()
      if (plan.kind === "resume" && s.chain < cfg.maxChain) {
        s.chain += 1
        schedule(sessionID, backoff(s.chain, cfg.baseDelayMs), plan)
      } else {
        toast(`${RESUME_TAG}: Could not resume (${err?.message ?? "error"}).`, "error")
      }
    }
  }

  // ── central failure handler ────────────────────────────────────────
  const handleError = async (sessionID, error) => {
    if (sessions.get(sessionID)?.child) {
      log("info", "ignoring error in subagent session (parent orchestrates)", { sessionID })
      return
    }
    const s = state(sessionID)
    const nowMs = Date.now()
    // Dedupe only the SAME incident (session.error + message.updated both fire);
    // anything recurring after a dispatched resume is a new incident.
    const sig = `${error?.name}:${error?.data?.statusCode ?? ""}:${error?.data?.message ?? ""}`
    const duplicateIncident =
      sig === s.lastErrorSig && nowMs - s.lastErrorAt < 2_000 && s.lastResumeAt <= s.lastErrorAt
    if (duplicateIncident) return
    s.lastErrorSig = sig
    s.lastErrorAt = nowMs
    s.lastActivity = nowMs
    if (error?.name) s.lastErrorName = error.name

    const kind = classify(error)
    log("warn", `session error (${kind})`, {
      sessionID, name: error?.name, statusCode: error?.data?.statusCode, message: error?.data?.message,
    })

    if (kind === "abort") { toast(`${RESUME_TAG}: Turn aborted — not resuming (user request).`, "info"); return }
    if (kind === "auth") {
      // Auth is provider-scoped: rotate to another PROVIDER's model if possible.
      if (cfg.switchOnQuota && (await rotateAwayFrom(sessionID, "authentication failed"))) {
        s.chain += 1
        if (s.chain <= cfg.maxChain) { schedule(sessionID, cfg.baseDelayMs, { kind: "resume", prompt: PROMPTS.resume }); return }
      }
      toast(`${RESUME_TAG}: Provider authentication failed — run \`opencode auth login\`.`, "error")
      return
    }

    // ── quota / free-tier exhaustion → rotate model, no user input ──
    if (kind === "quota") {
      if (cfg.switchOnQuota && (await rotateAwayFrom(sessionID, "quota/free tier exhausted"))) {
        schedule(sessionID, cfg.baseDelayMs, { kind: "resume", prompt: PROMPTS.resume })
        return
      }
      toast(`${RESUME_TAG}: Quota exhausted and no alternate model available — manual action needed.`, "error")
      return
    }

    // ── repeated rate limits on the same model → rotate too ──
    if (kind === "rate_limit" && s.rlStreak + 1 >= cfg.rlSwitchAfter &&
        cfg.switchOnRateLimit && (await rotateAwayFrom(sessionID, "repeated rate limits"))) {
      s.rlStreak = 0
      schedule(sessionID, jitter(Math.min(cfg.baseDelayMs, 15_000)), { kind: "resume", prompt: PROMPTS.resume })
      return
    }

    if (kind === "output_length") {
      if (s.continueCount >= cfg.outputLengthMax) {
        toast(`${RESUME_TAG}: Output kept hitting max length ${cfg.outputLengthMax}x — giving up.`, "warning")
        return
      }
      s.continueCount += 1
      schedule(sessionID, cfg.nudgeDelayMs, { kind: "continue", prompt: PROMPTS.truncated })
      return
    }

    if (kind === "overflow") {
      if (!cfg.compactOnOverflow || s.compactAttempted) {
        toast(`${RESUME_TAG}: Context window exhausted${s.compactAttempted ? " (compaction already tried)" : ""}.`, "error")
        return
      }
      s.compactAttempted = true
      s.awaitingCompactionSince = Date.now()
      detach(async () => {
        const summarizeWith = async (model) => {
          const body = model ? { providerID: model.providerID, modelID: model.modelID } : undefined
          await client.session.summarize({ path: { id: sessionID }, body })
        }
        try {
          await summarizeWith(s.currentModel ?? s.lastModel)
          log("info", "compaction requested after overflow", { sessionID })
        } catch (err) {
          // The summarizer model itself may be the problem (quota, outage) —
          // fall back to the best alternate model for this one-shot job.
          log("warn", "compaction failed on primary model, rotating summarizer", {
            sessionID, err: err?.message ?? String(err),
          })
          const alt = await pickAlternateModel(s.currentModel ?? s.lastModel)
          if (!alt) {
            toast(`${RESUME_TAG}: Compaction failed and no alternate model available.`, "error")
            return
          }
          await summarizeWith(alt)
          log("info", "compaction requested on alternate model", { sessionID, model: modelKey(alt) })
        }
        setTimeout(() => {
          const cur = state(sessionID)
          if (cur.awaitingCompactionSince) {
            cur.awaitingCompactionSince = 0
            toast(`${RESUME_TAG}: Compaction did not complete — not resuming.`, "error")
          }
        }, 180_000).unref?.()
      }, "summarize")
      return
    }

    if (kind === "fatal") {
      toast(`${RESUME_TAG}: Unrecoverable error (${error?.name ?? "unknown"}) — not retrying.`, "error")
      return
    }

    // ── retryable | rate_limit(first strikes) ──
    if (kind === "rate_limit") s.rlStreak += 1

    // Persistent model-specific trouble (endpoint down, network errors, 5xx
    // waves, timeouts): after N failed rounds on the same model, move on.
    // No cooldown penalty — provider outages are usually temporary.
    if (kind === "retryable") {
      s.failStreak += 1
      if (cfg.switchOnFailures && s.failStreak >= cfg.rotateAfterFailures &&
          (await rotateAwayFrom(sessionID, "persistent failures", false))) {
        s.failStreak = 0
        schedule(sessionID, jitter(Math.min(cfg.baseDelayMs, 15_000)), { kind: "resume", prompt: PROMPTS.resume })
        return
      }
    }

    if (s.pendingResume) return
    if (s.chain >= cfg.maxChain) {
      noteResumeFailure()
      toast(`${RESUME_TAG}: Gave up after ${s.chain} recovery attempts (${kind}). Send a message to try manually.`, "error")
      return
    }
    s.pendingResume = true
    s.chain += 1
    const delay = kind === "rate_limit"
      ? (retryAfterMs(error) ?? backoff(s.chain, cfg.rateLimitBaseMs))
      : backoff(s.chain, cfg.baseDelayMs)
    schedule(sessionID, delay, { kind: "resume", prompt: PROMPTS.resume })
  }

  // ── permission autopilot ───────────────────────────────────────────
  const denyList = () => {
    const extra = cfg.extraDeny.split(",").map((x) => x.trim()).filter(Boolean)
    return [...DANGEROUS_PATTERNS, ...extra]
  }
  const looksDangerous = (perm) => {
    const blob = JSON.stringify({ t: perm.title, m: perm.metadata, c: perm.callID }).toLowerCase()
    return denyList().some((entry) => {
      if (entry.startsWith("re:")) {
        try { return new RegExp(entry.slice(3), "i").test(blob) } catch { return false }
      }
      return blob.includes(entry.toLowerCase())
    })
  }

  const respondToPermission = async (sessionID, perm, response, why) => {
    const fn =
      client.session?.postSessionByIdPermissionsByPermissionId ??
      client.session?.respondToPermission ??
      client.session?.postSessionIdPermissionsPermissionId
    if (!fn) { log("warn", "permission API unavailable on this opencode version"); return false }
    try {
      await fn.call(client.session, {
        path: { id: sessionID, permissionID: perm.id },
        body: { response },
      })
      log("info", `permission auto-${response}`, { sessionID, type: perm.type, why })
      toast(`${RESUME_TAG}: auto-${response} ${perm.type} permission (${why}).`, response === "reject" ? "warning" : "info")
      return true
    } catch (err) {
      log("warn", "permission respond failed", { sessionID, err: err?.message ?? String(err) })
      return false
    }
  }

  const EDIT_TYPES = ["edit", "write", "patch", "file", "apply_patch"]
  const SHELL_TYPES = ["bash", "shell", "command", "terminal", "execute"]
  const WEB_TYPES = ["webfetch", "fetch", "web", "url"]

  const decidePermission = (perm) => {
    if (!cfg.autonomy || !cfg.permissions) return null
    if (cfg.permissionMode === "off") return null
    const type = String(perm.type ?? "").toLowerCase()
    if (looksDangerous(perm)) return "reject"
    if (EDIT_TYPES.includes(type) || WEB_TYPES.includes(type)) return "once"
    if (SHELL_TYPES.includes(type)) return "once" // danger already checked above
    if (cfg.permissionMode === "all") return "once"
    return null // safe mode: unknown types stay human-decided
  }

  // ── idle evaluation: success reset, todo drive, proposals ─────────
  const budgetLeft = (s) =>
    !cfg.budgetMs || !s.taskStartAt || Date.now() - s.taskStartAt < cfg.budgetMs

  const evaluateIdle = async (sessionID) => {
    const s = state(sessionID)
    const relevant =
      s.lastErrorName || s.lastResumeAt || s.continueCount ||
      s.todos.length || s.lastTurnHadText
    s.awaitingCompactionSince = 0
    if (!relevant) return

    let entries = []
    try {
      const res = await client.session.messages({ path: { id: sessionID } })
      entries = (res?.data ?? res) ?? []
    } catch { return }

    let lastAssistant = null
    for (let i = entries.length - 1; i >= 0; i -= 1) {
      if (entries[i]?.info?.role === "assistant") { lastAssistant = entries[i]; break }
    }
    if (!lastAssistant) return

    const info = lastAssistant.info
    if (info.modelID && !s.currentModel) {
      s.lastModel = { providerID: info.providerID, modelID: info.modelID }
      s.originalModel = s.originalModel ?? s.lastModel
    }

    const hasContent = (lastAssistant.parts ?? []).some((p) => ["text", "tool", "reasoning"].includes(p?.type))
    const errored = Boolean(info.error)

    if (!errored && hasContent) {
      noteSuccess()
      s.toolErrs = 0

      const todos = s.todos ?? []
      const open = todos.filter((t) => t.status === "pending" || t.status === "in_progress")
      const finished = todos.filter((t) => t.status === "completed" || t.status === "cancelled")

      // The agent ended its turn by asking a question or announcing more
      // work ("Continue to finalize.") instead of finishing — keep it going.
      if (open.length === 0 && cfg.autonomy && cfg.proceedOnAsk &&
          s.proceedCount < cfg.maxProceeds && s.nudges < cfg.maxNudges && budgetLeft(s)) {
        const text = (lastAssistant.parts ?? [])
          .map((x) => (x?.type === "text" ? x.text : "")).join(" ")
        if (text && text.trim()) {
          const asked = QUESTION_PATTERNS.some((re) => re.test(text))
          const stubbed = looksLikeContinuationStub(text) || looksLikeContinuationLong(text)
          if (asked || stubbed) {
            s.proceedCount += 1
            s.nudges += 1
            log("info", asked ? "agent asked a question — proceeding autonomously" : "agent announced continuation but stopped — resuming", { sessionID })
            schedule(sessionID, cfg.nudgeDelayMs, {
              kind: "proceed",
              prompt: asked ? PROMPTS.proceed : PROMPTS.keepGoing,
            })
            return
          }
        }
      }

      // Full completion → self-improvement passes → wrap-up proposals → toast
      if (todos.length > 0 && open.length === 0) {
        if (cfg.autonomy && cfg.improveLoop && s.improveDone < cfg.improveCycles &&
            s.nudges < cfg.maxNudges && budgetLeft(s)) {
          s.improveDone += 1
          s.nudges += 1
          log("info", "improvement pass", { sessionID, cycle: `${s.improveDone}/${cfg.improveCycles}` })
          schedule(sessionID, cfg.nudgeDelayMs, {
            kind: "improve",
            prompt: () => PROMPTS.improve(s.improveDone, cfg.improveCycles),
          })
          return
        }
        if (cfg.autonomy && cfg.proposals && !s.proposalSent && s.nudges < cfg.maxNudges && budgetLeft(s)) {
          s.proposalSent = true
          s.nudges += 1
          schedule(sessionID, cfg.nudgeDelayMs, { kind: "propose", prompt: PROMPTS.propose })
          return
        }
        toast(`${RESUME_TAG}: Task list complete. ✅`, "success")
        return
      }

      // Unfinished todos → drive continuation (with spin detection + caps)
      if (cfg.autonomy && cfg.todoDrive && open.length > 0 &&
          s.nudges < cfg.maxNudges && budgetLeft(s)) {
        if (finished.length === s.lastDriveCompleted) {
          s.staleDrives += 1
        } else {
          s.staleDrives = 0
          s.lastDriveCompleted = finished.length
        }
        if (s.staleDrives < 2) {
          s.nudges += 1
          s.driveCount += 1
          log("info", "todo-drive nudge", { sessionID, open: open.length, drive: s.driveCount })
          schedule(sessionID, cfg.nudgeDelayMs, { kind: "todos", prompt: PROMPTS.todos })
          return
        }
        log("warn", "todo-drive stopped: no progress across nudges", { sessionID })
        toast(`${RESUME_TAG}: Todos stalled without progress — stopping auto-drive.`, "warning")
        return
      }
      return
    }

    if (!errored && !hasContent && s.lastResumeAt && s.emptyNudges < 1) {
      s.emptyNudges += 1
      log("info", "empty response detected, nudging", { sessionID })
      schedule(sessionID, cfg.nudgeDelayMs, { kind: "empty", prompt: PROMPTS.empty })
    }
  }

  // ── stall + stuck-retry watchdog ───────────────────────────────────
  const takeover = (sessionID, why, toastMsg) => {
    const s = state(sessionID)
    if (s.chain >= cfg.maxChain || s.stallResumes >= 2) return
    s.stallResumes += 1
    s.chain += 1
    s.lastActivity = Date.now()
    s.retryEnteredAt = 0
    s.retryNext = 0
    log("warn", why, { sessionID })
    toast(toastMsg)
    detach(async () => {
      try { await client.session.abort({ path: { id: sessionID } }) } catch { /* already dead */ }
      setTimeout(() => schedule(sessionID, 800, { kind: "resume", prompt: PROMPTS.resume }), 1_500).unref?.()
    }, "takeover-abort")
  }

  const checkStalls = () => {
    const nowMs = Date.now()
    for (const [sessionID, s] of sessions) {
      if (s.child) continue

      // A session parked in OpenCode's internal retry loop can wait for a
      // provider-specified Retry-After of effectively unlimited length.
      // If it sits there too long, or the next attempt is absurdly far in
      // the future, take over: abort and resume on our own terms.
      if (s.status === "retry") {
        const enteredAt = s.retryEnteredAt || nowMs
        const nextIn = s.retryNext ? s.retryNext - nowMs : 0
        const absurdFuture = Boolean(s.retryNext) && nextIn > cfg.retryFutureCapMs
        const tooLong = nowMs - enteredAt > cfg.retryTakeoverMs
        if (absurdFuture || tooLong) {
          takeover(sessionID,
            absurdFuture
              ? "retry loop scheduled absurdly far ahead — taking over"
              : "retry loop exceeded takeover limit — taking over",
            `${RESUME_TAG}: Retry loop is stuck — taking over.`)
        }
        continue
      }

      if (s.status !== "busy") continue
      if (permissionPending.has(sessionID)) continue
      // A genuinely running tool gets an extended grace window: quiet builds,
      // installs, test suites are legitimate silence, not stalls.
      const silenceLimit = s.toolRunning
        ? cfg.stallTimeoutMs * cfg.runningToolFactor
        : cfg.stallTimeoutMs
      if (nowMs - s.lastActivity < silenceLimit) continue
      takeover(sessionID, "stalled stream detected, aborting + resuming",
        `${RESUME_TAG}: Response appears stuck — restarting it.`)
    }
  }

  // ── crash recovery: revive sessions killed by a server/machine restart ──
  // Recovery timers live in the server process, so a crash orphans any turn
  // that was mid-recovery or awaiting its first reply. On startup we scan
  // recent sessions and give those a fresh continuation.
  const reanimate = async () => {
    if (!cfg.reanimate) return
    let list = []
    try {
      const res = await client.session.list()
      list = (res?.data ?? res) ?? []
    } catch (err) {
      log("warn", "reanimation scan failed", { err: err?.message ?? String(err) })
      return
    }
    if (!Array.isArray(list)) return
    const cutoff = Date.now() - cfg.reanimateWindowMs
    for (const sess of list) {
      if (!sess?.id || sess.parentID) continue // subagents belong to parents
      if ((sess.time?.updated ?? 0) < cutoff) continue // too old to be a crash victim
      const s = state(sess.id)
      if (s.reanimated) continue
      s.reanimated = true

      let entries = []
      try {
        const r = await client.session.messages({ path: { id: sess.id } })
        entries = (r?.data ?? r) ?? []
      } catch { continue }
      if (!entries.length) continue
      const lastEntry = entries[entries.length - 1]
      const lastInfo = lastEntry?.info
      if (!lastInfo) continue

      resetTaskScope(s)

      // A prompt that never received any reply: the turn died at submission.
      if (lastInfo.role === "user") {
        log("info", "reanimating session with unanswered prompt", { sessionID: sess.id })
        schedule(sess.id, 1_500, { kind: "resume", prompt: PROMPTS.resume })
        toast(`${RESUME_TAG}: Revived a session interrupted by the restart.`)
        continue
      }

      if (lastInfo.role === "assistant" && lastInfo.error) {
        const kind = classify(lastInfo.error)
        if (["abort", "auth", "fatal", "overflow"].includes(kind)) continue
        if (lastInfo.modelID) {
          s.lastModel = { providerID: lastInfo.providerID, modelID: lastInfo.modelID }
        }
        if (kind === "quota" || kind === "rate_limit") {
          await rotateAwayFrom(sess.id, "quota/rate limit (after restart)", true)
        }
        log("info", "reanimating interrupted session", { sessionID: sess.id, kind })
        schedule(
          sess.id,
          1_500,
          kind === "output_length"
            ? { kind: "continue", prompt: PROMPTS.truncated }
            : { kind: "resume", prompt: PROMPTS.resume },
        )
        toast(`${RESUME_TAG}: Revived a session interrupted by the restart.`)
      }
    }
  }

  if (cfg.enabled) {
    const wd = setInterval(() => detach(checkStalls, "watchdog"), cfg.watchdogMs)
    wd.unref?.()
    detach(() => log("debug", "auto-resume plugin initialized"), "init-log")
    detach(reanimate, "reanimate")
  } else {
    console.warn(`${RESUME_TAG} disabled via OPENCODE_RESUME_ENABLED`)
  }

  return {
    event: async ({ event }) => {
      if (!cfg.enabled) return
      try {
        const type = event?.type
        const p = event?.properties ?? {}

        switch (type) {
          case "session.error": {
            if (p.sessionID && p.error) detach(handleError(p.sessionID, p.error), "handleError")
            break
          }

          case "message.updated": {
            const info = p.info
            if (!info?.sessionID) break
            state(info.sessionID).lastActivity = Date.now()

            if (info.role === "user") {
              // Fresh task boundary — unless it's OUR own injected prompt.
              // UserMessage carries no parts in this event, so verify by
              // fetching the stored message text and matching our tag.
              const s0 = state(info.sessionID)
              let ours = false
              if (info.id) {
                try {
                  const res = await client.session.message({
                    path: { id: info.sessionID, messageID: info.id },
                  })
                  const data = res?.data ?? res
                  const text = (data?.parts ?? [])
                    .map((x) => (x?.type === "text" ? x.text : "")).join(" ")
                  ours = text.includes(RESUME_TAG)
                } catch { ours = false }
              }
              if (!ours) {
                resetTaskScope(s0)
                s0.currentModel = null
                s0.emptyNudges = 0
              }
              s0.lastTurnHadText = false // new turn begins
              break
            }

            if (info.role === "assistant") {
              if (info.modelID) {
                const s = state(info.sessionID)
                const seen = { providerID: info.providerID, modelID: info.modelID }
                s.originalModel = s.originalModel ?? seen
                s.lastModel = seen
              }
              if (info.error) detach(handleError(info.sessionID, info.error), "handleError")
            }
            break
          }

          case "message.part.updated": {
            const part = p.part
            if (!part?.sessionID) break
            const s = state(part.sessionID)
            s.lastActivity = Date.now()
            if (part.type === "text" && typeof part.text === "string" && part.text.trim()) {
              s.lastTurnHadText = true
            } else if (part.type === "tool") {
              const st = part.state?.status
              if (st === "running") {
                s.toolRunning = true // heartbeat: long-running tools get grace
              } else if (st === "completed" || st === "error") {
                s.toolRunning = false
              }
              if (st === "error") {
                s.toolErrs += 1
                if (cfg.autonomy && cfg.debugNudge && s.toolErrs >= 3 && !s.debugArmed &&
                    s.nudges < cfg.maxNudges && budgetLeft(s)) {
                  s.debugArmed = true
                  s.nudges += 1
                  log("warn", "consecutive tool failures — sending debug nudge", {
                    sessionID: part.sessionID, fails: s.toolErrs,
                  })
                  schedule(part.sessionID, cfg.nudgeDelayMs, { kind: "debug", prompt: PROMPTS.debug })
                }
              } else if (st === "completed") {
                s.toolErrs = 0
                s.debugArmed = false
              }
            }
            break
          }

          case "todo.updated": {
            if (p.sessionID && Array.isArray(p.todos)) state(p.sessionID).todos = p.todos
            break
          }

          case "session.status": {
            if (!p.sessionID) break
            const s = state(p.sessionID)
            s.status = p.status?.type ?? "unknown"
            s.lastActivity = Date.now()
            if (s.status === "retry") {
              if (!s.retryEnteredAt) s.retryEnteredAt = Date.now()
              if (typeof p.status?.next === "number") s.retryNext = p.status.next
            } else {
              s.retryEnteredAt = 0
              s.retryNext = 0
            }
            if (s.status === "busy") s.lastTurnHadText = false
            if (s.status === "idle") {
              s.pendingResume = false
              detach(evaluateIdle(p.sessionID), "evaluateIdle")
            }
            break
          }

          case "session.idle": {
            if (p.sessionID) {
              const s = state(p.sessionID)
              s.status = "idle"
              s.pendingResume = false
              detach(evaluateIdle(p.sessionID), "evaluateIdle")
            }
            break
          }

          case "permission.updated":
          case "permission.asked": {
            if (!p.sessionID) break
            permissionPending.set(p.sessionID, Date.now()) // always: watchdog depends on it
            if (!p.id) break
            const decision = decidePermission(p)
            if (decision) {
              detach(respondToPermission(p.sessionID, p, decision,
                decision === "reject" ? "dangerous pattern" : "autopilot"), "permission")
            }
            break
          }

          case "permission.replied": {
            if (p.sessionID) permissionPending.delete(p.sessionID)
            break
          }

          case "session.created":
          case "session.updated": {
            const info = p.info
            if (info?.id) {
              const s = state(info.id)
              if (info.parentID) s.child = true
            }
            break
          }

          case "session.compacted": {
            const s = sessions.get(p.sessionID)
            if (s?.awaitingCompactionSince) {
              s.awaitingCompactionSince = 0
              log("info", "compaction done, resuming", { sessionID: p.sessionID })
              schedule(p.sessionID, 3_000, { kind: "resume", prompt: PROMPTS.resume })
            }
            break
          }

          case "session.deleted": {
            const id = p.info?.id ?? p.sessionID
            if (id) {
              sessions.delete(id)
              permissionPending.delete(id)
              const t = timers.get(id)
              if (t) clearTimeout(t)
              timers.delete(id)
            }
            break
          }
        }
      } catch (err) {
        console.error(`${RESUME_TAG} event handler error:`, err?.message ?? err)
      }
    },
  }
}

