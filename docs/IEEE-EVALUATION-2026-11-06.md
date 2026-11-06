# IEEE V&V Evaluation — Duet and Zoe

**Date:** 2026-11-06
**Evaluator:** automated agent (OpenCode)
**Scope:** `/root/Duet--Digital-Twin-Technology` (live at `https://saikarun-duet-digital-twin.static.hf.space`) and `/root/zoe` (local Python/MCP rig)
**Method:** IEEE 1012-2016 (System/Software V&V) with IEEE 29119-3-2021 test documentation, IEEE 42010-2022 architecture review, and ISO/IEC 25010:2023 quality parameters
**Classification:** self-assessment / internal V&V, **not** a certification

---

## 0. Executive summary

| Project | IEEE 1012 integrity level | V&V task coverage | Quality score (ISO 25010, /5) | Verdict |
|---|---|---|---|---|
| **Duet** | IL2 (moderate) | **47%** (7.5 / 16 applicable tasks) | **3.1** | **Conditional pass** — demo/research only |
| **Zoe** | IL2 (moderate) | **67%** (10 / 15 applicable tasks) | **3.9** | **Conditional pass** — local/research use only |

Neither system is production-certifiable today. The blockers are specific and fixable:

- **Duet:** no automated tests, no CSP, no clickjacking protection, API keys in `localStorage`.
- **Zoe:** MCP tool inputs are unbounded (CPU denial-of-service), ledger redaction is narrow, one quality metric still fails (M-4.2), and the "LoRA" claim is a controller, not merged weights.

**Strix was not executed** — this environment has no Docker daemon and no LLM API key. The report marks it `NOT RUN` rather than implying coverage that does not exist.

---

## 1. Evaluation mechanism (what "IEEE" means here)

### 1.1 Standards applied

| Standard | Role in this evaluation |
|---|---|
| **IEEE 1012-2016** | Defines V&V integrity levels (IL1–IL4) and the V&V task set used as the compliance matrix |
| **IEEE 29119-3-2021** | Test documentation model: test plan, design, cases, procedures, results, status |
| **IEEE 42010-2022** | Architecture-description review (views, stakeholders, concerns, rationale) |
| **IEEE 7000-2021** | Ethical-concern analysis for AI companion / dual-use behaviour |
| **IEEE 24765-2017** | Vocabulary used for anomaly and defect classification |
| **ISO/IEC 25010:2023** | Quality-parameter taxonomy ("other parameters"): functional suitability, performance, compatibility, usability, reliability, security, maintainability, portability |

### 1.2 Integrity level assignment (IEEE 1012 §5)

| Project | Level | Rationale |
|---|---|---|
| Duet | **IL2** | Public web app; failure causes privacy/reputational harm (BYOK key exposure) but no physical safety, no server-side PII, no financial transaction |
| Zoe | **IL2** | Local developer/companion tool; failure causes incorrect output or local resource exhaustion; `MockVM` and allowlisted egress mean no real sandbox escape path today. Would become **IL3** if deployed to vulnerable users or given real actuation |

### 1.3 Evidence sources

| Source | Type | Status |
|---|---|---|
| `pytest` (Zoe) | functional / integration | **RUN** — 115 passed |
| `tsc --noEmit` (Duet) | static type analysis | **RUN** — pass |
| `ruff` targeted (Zoe) | static analysis | **RUN** — pass (`F821`, `F541`, `I001`) |
| `pip check` (Zoe) | dependency consistency | **RUN** — no broken requirements |
| Secret-pattern scan (both) | security / supply chain | **RUN** — none found |
| Live HTTP header + TLS audit (Duet) | deployment security | **RUN** (Observatory-equivalent) |
| Mozilla HTTP Observatory | web security scoring | **PARTIAL** — official API retired/unreachable (see §1.4) |
| Strix | agentic penetration test | **NOT RUN** — no Docker, no LLM key (see §1.5) |
| `npm audit` (Duet) | dependency CVEs | **NOT RUN** — registry request timed out |
| Accessibility (axe/Lighthouse) | usability | **NOT RUN** |
| Real-model latency (Zoe) | performance | **NOT RUN** — no GGUF/Ollama model installed |

### 1.4 Mozilla Observatory — why it is marked partial

- The legacy endpoint `https://observatory.mozilla.org/api/v2/analyze?host=…` returns **HTTP 404** for every host tested (including `example.com`), not just the target.
- The tool has moved to MDN (`https://developer.mozilla.org/en-US/observatory`); its new backend (`observatory-api.mdn.mozilla.net`) does not expose the documented `/api/v1/analyze` route publicly (404 on all probed routes).
- The MDN analyze page is a client-side SPA with no server-rendered result payload, so no official score could be extracted non-interactively.

**Substitute performed:** the same controls Observatory grades were measured directly from the live response (headers + TLS). Results in §3.1 are therefore *Observatory-equivalent*, not an official letter grade.

### 1.5 Strix — why it is marked not run

Strix requires **Docker running** and an **LLM API key** (or a paid cloud account). This host has neither:

```
docker      -> not installed
OPENAI/ANTHROPIC/GEMINI/OPENROUTER/NVIDIA/GLAMA keys -> all unset
```

Running an autonomous pentest also requires explicit authorization for the target. The correct command set is recorded in §7 so the scan can be executed later without re-deriving it.

---

## 2. IEEE 1012 V&V task matrix

Legend: **P** = performed, **A** = partial, **N** = not performed, **—** = not applicable.

| # | IEEE 1012 V&V task | Duet | Zoe | Evidence |
|---|---|---|---|---|
| 1 | V&V planning | A | A | No formal IEEE 1012/29119 plan in either repo |
| 2 | Hazard / risk analysis | N | A | Zoe has premortem + failure-mode docs; Duet has none |
| 3 | Requirements traceability | A | P | Zoe maps FR-1.x…FR-11.x to code/tests; Duet has prose only |
| 4 | Architecture description review | P | P | Duet README "How it works"; Zoe `docs/ARCHITECTURE.md` |
| 5 | Interface / API analysis | A | P | Duet provider table; Zoe MCP `inputSchema` + backend interface |
| 6 | Static analysis / code review | P | P | `tsc`, `ruff`; manual review of both |
| 7 | Unit testing | N | P | Duet has no test files; Zoe 115 tests |
| 8 | Integration / system testing | A | P | Duet CI builds but does not test behaviour; Zoe full-rig tests |
| 9 | Security testing (Strix/DAST) | N | N | Tool unavailable (§1.5) |
| 10 | HTTP security posture | A | — | Observatory-equivalent audit only (§3.1); Zoe has no web surface |
| 11 | Dependency / supply-chain audit | N | A | `npm audit` timed out; `pip check` passed but no CVE scan |
| 12 | Performance / efficiency | A | A | Duet bundle sizes; Zoe mock latency only |
| 13 | Privacy / data protection | A | A | Duet keys in localStorage; Zoe redaction + local ledger |
| 14 | Deployment / operational verification | P | A | Duet live URL verified; Zoe Termux/desktop doctor verified, no production deployment |
| 15 | Regression / change control | P | P | Git history + CI in both repos |
| 16 | Independent V&V | N | N | Self-assessment only |

**Coverage (excluding N/A, A counts 0.5):**

- Duet: (4 P + 0.5 × 7 A) / 16 = **47%**
- Zoe: (7 P + 0.5 × 6 A) / 15 = **67%**

These percentages measure *task coverage*, not defect-free status.

---

## 3. Results by project

### 3.1 Duet — live HTTP/TLS posture (2026-11-06)

Target: `https://saikarun-duet-digital-twin.static.hf.space/` → 302 → `/index.html` → 200

| Control | Observed | Verdict |
|---|---|---|
| TLS version | TLS 1.3, `TLS_AES_128_GCM_SHA256` | **PASS** |
| Certificate | `CN=*.static.hf.space`, Amazon RSA 2048 M01, verify 0 | **PASS** |
| HSTS | `strict-transport-security: max-age=31536000` | **PARTIAL** — no `includeSubDomains`, no `preload` |
| Content-Security-Policy | absent | **FAIL** |
| X-Content-Type-Options | absent | **FAIL** |
| X-Frame-Options / `frame-ancestors` | absent | **FAIL** |
| Referrer-Policy | `strict-origin-when-cross-origin` | **PASS** |
| Cross-Origin-Opener-Policy | `same-origin` | **PASS** |
| Cross-Origin-Resource-Policy | absent | **FAIL** |
| Permissions-Policy | absent | **FAIL** |
| CORS | `access-control-allow-origin: *` | **PARTIAL** — acceptable for public static assets, unnecessary for an app |
| Cookies | none set | **N/A** |
| SRI | no `integrity` attributes | **FAIL** (low impact: first-party bundles) |
| `x-powered-by` | `huggingface-moon` | **INFO** — minor fingerprinting |

**Observatory-equivalent band:** **D** (estimated; not an official score). The decisive losses are CSP, frame protection, `nosniff`, CORP, and Permissions-Policy.

### 3.2 Duet — build and behaviour

| Check | Result |
|---|---|
| `npm run typecheck` | **PASS** (exit 0) |
| CI | typecheck + `vite build` on Node 20/22 — **no behavioural tests** |
| Build artifact | `dist/` 883 KB: 288 KB JS + 460 KB JS + 75 KB CSS |
| Live HTML | `lang="en"`, viewport, `<noscript>`, canonical → HF Space, JSON-LD, Google Fonts preconnect |
| Secrets in source | none found |
| Key storage | `localStorage` (documented, BYOK) |

### 3.3 Zoe — functional and static results

| Check | Result |
|---|---|
| `pytest -q` | **PASS** — 115 tests |
| `zoe --mock run … --json` | **PASS** — 5-line output, `backend: mock`, `mock: true`, `degraded: false`, 22.2 ms e2e, 35 frames |
| `zoe --mock report` | **26 / 27 metrics**, `critical_five_ok=True`; **M-4.2 fails** (Dunce rate 0.375 vs < 0.20) |
| `zoe doctor` (desktop + Termux Python) | **PASS** — platform-aware hints, offline `--no-probe` works |
| `ruff` (`F821`, `F541`, `I001`) | **PASS** |
| `pip check` | **PASS** — no broken requirements |
| Secrets in source | none found |
| Risky constructs | no `shell=True`, no `eval`/`exec` on input, HTTP + subprocess calls have timeouts, engines default to localhost |
| MCP surface | 7 tools; schemas present; **inputs not bounded** (see Z-01); Emoja is consent-gated and deletable |
| Sandbox | `MockVM.exec()` stores commands, does **not** execute them; egress allowlist enforced |

---

## 4. ISO/IEC 25010 quality parameters

Scores are 0–5, judged for the project's stated purpose (research prototype / demo), not for production.

| Characteristic | Duet | Zoe | Notes |
|---|---|---|---|
| Functional suitability | 4 | 3 | Duet does what it claims; Zoe's adapter is a controller, reservoir is reduced |
| Performance efficiency | 3 | 4 | Duet 883 KB bundle, external fonts; Zoe 22 ms mock, real engine unmeasured |
| Compatibility | 4 | 4 | Duet modern browsers; Zoe Python 3.10+ / Termux |
| Usability | 3 | 4 | Duet polished UI but untested with users; Zoe clear CLI + doctor |
| Reliability | 2 | 3 | Duet no tests/monitoring; Zoe retries + visible degradation, M-4.2 fails |
| Security | 2 | 3 | Duet missing CSP/frame/nosniff, keys in localStorage; Zoe unbounded MCP inputs |
| Maintainability | 2 | 5 | Duet no test suite; Zoe 115 tests, docs, typed errors |
| Portability | 5 | 5 | Both run on commodity infrastructure |
| **Mean** | **3.1** | **3.9** | |

---

## 5. Findings and anomalies

Severity uses IEEE 1012 anomaly impact (Critical / High / Medium / Low). CWE is given for security items.

### 5.1 Duet

| ID | Severity | Finding | CWE | Remediation |
|---|---|---|---|---|
| **D-01** | **High** | No Content-Security-Policy | CWE-693 | Add a `<meta http-equiv="Content-Security-Policy">` with `default-src 'self'`, explicit `connect-src` for each provider, `img-src 'self' data: blob:`, `style-src 'self' 'unsafe-inline'` (Tailwind/inline styles). `frame-ancestors` is ignored in meta — set it at the host/CDN or use Vercel headers |
| **D-02** | **High** | Provider API keys stored in `localStorage`; combined with D-01, one XSS exfiltrates every key | CWE-522, CWE-79 | Offer memory-only or `sessionStorage` mode; add "forget keys" button; document the XSS threat model; never inject model output as HTML (`react-markdown` is safe by default — keep it that way) |
| **D-03** | Medium | Missing `X-Content-Type-Options: nosniff` | CWE-693 | Host header (Vercel `headers` config) or meta workaround where supported |
| **D-04** | Medium | No clickjacking protection (`X-Frame-Options` / `frame-ancestors`) | CWE-1021 | Host-level header; on HF static, document the gap or move to Vercel for header control |
| **D-05** | Medium | No automated behavioural tests; CI only typechecks and builds | — | Add Vitest/React Testing Library for provider adapters, stream parser, fallback paths; require tests in CI |
| **D-06** | Low | `access-control-allow-origin: *` on app responses | CWE-942 | Low risk for public static assets; restrict if the app ever handles authenticated data |
| **D-07** | Low | No `Permissions-Policy`; Google Fonts loaded from third party | — | Add `Permissions-Policy` (camera=(), microphone=(), geolocation=()); self-host fonts or accept the privacy trade-off |
| **D-08** | Low | Repo `index.html` canonical points to Vercel while the deployed Space rewrites it to HF | — | Parameterise canonical per deployment to avoid duplicate-content signals |
| **D-09** | Unknown | Dependency CVEs unverified (`npm audit` timed out) | — | Run `npm audit --omit=dev` in CI; add Dependabot (already configured remotely) |

**Positives:** TLS 1.3, valid certificate, HSTS 1 year, COOP `same-origin`, strict referrer policy, typecheck clean, no secrets committed, keys never sent to a Duet server (there is no server).

### 5.2 Zoe

| ID | Severity | Finding | CWE | Remediation |
|---|---|---|---|---|
| **Z-01** | **High** | MCP inputs unbounded: `zoe_report.generations` is `int()`-cast with no cap; `zoe_run.text` has no length limit | CWE-400 | Clamp `generations` to e.g. 1–1000 and `text` to e.g. 8–16 KB; reject non-numeric types with a JSON-RPC error |
| **Z-02** | Medium | Ledger redaction covers email, card-like numbers, `sk-…`/`ghp_…` keys, and `password:` — misses AWS keys, JWTs, bearer tokens, private-key blocks | CWE-532 | Extend `_PATTERNS`; add tests with representative secrets; redact before every persistence path |
| **Z-03** | Medium | `MCPClient.connect()` spawns `subprocess.Popen` with no timeout or teardown | CWE-400 | Add handshake timeout, terminate/kill on failure, track and reap children |
| **Z-04** | Medium | The "evolving LoRA" is a controller that steers temperature/tone; it is not merged into the base weights | — | Already documented honestly in README; keep the wording, or implement adapter merge in the `llamacpp` path |
| **Z-05** | Medium | `M-4.2 Dunce rate` = 0.375 vs target < 0.20 | — | Documented as known; either improve the mutation proposal (SPSA/guided) or formally re-scope the target |
| **Z-06** | Low | `zoe/mcp_server.py` still labels L3 "llama.cpp + LoRA" after the backend refactor | — | Update the `LAYERS` constant to "Frozen base + LoRA (pluggable engine)" |
| **Z-07** | Low | L7 `MockVM` is not a real sandbox; `FirecrackerVM` is a stub | — | Keep `vm.run` internal; do not present L7 as an isolation boundary until a real backend exists |
| **Z-08** | Unknown | No CVE scan of `numpy`/optional `llama-cpp-python` | — | Add `pip-audit` to CI |
| **Z-09** | Info | Termux/desktop parity is real; backend selection is localhost-only and fails visibly | — | None |

**Positives:** 115 tests, Emoja consent-gated with tested deletion, typed `BackendUnavailable`/`BackendError`, retry with cooldown, degraded flag surfaced in `RunResult`, no `shell=True`, HTTP timeouts, localhost defaults, egress allowlist, redaction before ledger write, honest documentation of mock paths.

---

## 6. IEEE 1012 verdict

| Project | Verdict | Conditions |
|---|---|---|
| **Duet** | **Conditional pass (IL2)** | Acceptable as a public demo/research artifact. Before promoting as production: close D-01, D-02, D-03, D-04; add behavioural tests (D-05); complete dependency audit (D-09) |
| **Zoe** | **Conditional pass (IL2)** | Acceptable as a local/research rig. Before exposing the MCP server to untrusted clients: close Z-01, Z-02, Z-03; resolve or re-scope Z-04/Z-05; complete dependency audit (Z-08) |

**Not certified.** IEEE 1012 certification requires independent V&V, formal test documentation, and the security testing that Strix would provide. Those are `NOT RUN` and are not implied by this report.

**TRL impact:** unchanged from the prior assessment — Duet **TRL 5**, Zoe **TRL 4**. Security hardening does not move TRL by itself; operational evidence and independent evaluation do.

---

## 7. Reproduction

### 7.1 Mozilla Observatory (official, when reachable)

```bash
# MDN UI (interactive, official score)
open "https://developer.mozilla.org/en-US/observatory/analyze?host=saikarun-duet-digital-twin.static.hf.space"

# Legacy API is retired (404); do not script against it.
```

### 7.2 Observatory-equivalent manual audit

```bash
curl -sSI https://saikarun-duet-digital-twin.static.hf.space/index.html
echo | openssl s_client -connect saikarun-duet-digital-twin.static.hf.space:443 \
  -servername saikarun-duet-digital-twin.static.hf.space 2>/dev/null \
  | grep -E 'Protocol|Cipher|Verify return'
```

### 7.3 Strix (requires Docker + LLM key + authorization)

```bash
curl -sSL https://strix.ai/install | bash
export STRIX_LLM="openrouter/z-ai/glm-5.3"     # or any LiteLLM provider
export LLM_API_KEY="…"

# White-box, both projects
strix -n --target /root/Duet--Digital-Twin-Technology --scan-mode quick
strix -n --target /root/zoe --scan-mode quick

# Black-box, live Duet Space (only with owner authorization)
strix -n --target https://saikarun-duet-digital-twin.static.hf.space --scan-mode quick

# CI gate
strix -n --target ./ --scan-mode quick --fail-on high
```

### 7.4 Project checks

```bash
# Duet
cd /root/Duet--Digital-Twin-Technology
npm run typecheck
npm run build
npm audit --omit=dev

# Zoe
cd /root/zoe
/usr/bin/python3 -m pytest -q
/usr/bin/python3 -m zoe --mock report
/usr/bin/python3 -m zoe doctor
```

---

## 8. Prioritized remediation backlog

| Priority | Item | Owner action |
|---|---|---|
| P0 | D-01 CSP + D-02 key handling | Duet — add meta CSP, memory-only key option, document XSS model |
| P0 | Z-01 MCP input caps | Zoe — clamp text/generations, reject wrong types |
| P1 | D-03/D-04 nosniff + frame protection | Duet — host headers (Vercel) or document HF limitation |
| P1 | Z-02 redaction coverage | Zoe — AWS/JWT/bearer/private-key patterns + tests |
| P1 | Z-03 MCP child-process lifecycle | Zoe — handshake timeout, terminate, reap |
| P2 | D-05 / Z-08 dependency + behavioural tests | Both — add test suites and `pip-audit`/`npm audit` to CI |
| P2 | Z-05 M-4.2 | Zoe — improve mutation proposal or re-scope |
| P3 | Z-06 L3 label drift, D-08 canonical | Both — documentation/metadata fixes |
| P3 | Strix + Observatory official runs | Both — execute in a Docker-capable environment with keys |

---

## Appendix A — raw evidence snapshot

```text
Duet live headers (2026-11-06):
  HTTP/2 200
  strict-transport-security: max-age=31536000
  cross-origin-opener-policy: same-origin
  referrer-policy: strict-origin-when-cross-origin
  access-control-allow-origin: *
  (no content-security-policy, x-content-type-options, x-frame-options,
   permissions-policy, cross-origin-resource-policy)
  TLSv1.3 TLS_AES_128_GCM_SHA256, verify 0

Duet build:
  tsc --noEmit: exit 0
  dist: 883K (288K js + 460K js + 75K css)

Zoe:
  pytest: 115 passed
  run: backend=mock mock=true degraded=false e2e=0.0222s frames=35
  report: scored=27 passed=26; M-4.2 Dunce rate 0.375 (want <0.20)
  ruff (F821,F541,I001): pass
  pip check: pass
  secrets scan: none

Environment limits:
  docker: not installed
  LLM API keys: unset
  observatory.mozilla.org/api/v2/analyze: HTTP 404
  observatory-api.mdn.mozilla.net/api/v1/analyze: HTTP 404
```
