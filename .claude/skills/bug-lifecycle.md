# Skill: Bug Lifecycle — Report → Reproduce → Fix → Validate → Close

Every bug — whether reported by a user, found in testing, or noticed during development — must go through this complete lifecycle. **A bug is NOT fixed until it is validated on the live site.**

## Phase 1: Report & Triage

**Goal**: Understand what's broken and where.

1. **Capture the report** — What did the user say? What were they doing? What screen/page?
2. **Classify severity**:
   - **P0 Critical**: Site down, data loss, auth broken → fix immediately
   - **P1 High**: Feature broken, can't complete workflow → fix same session
   - **P2 Medium**: UI issue, cosmetic, workaround exists → fix when convenient
3. **Identify affected area** — Use the classification table in `debugging.md` Step 1

## Phase 2: Reproduce

**Goal**: See the bug yourself. If you can't reproduce it, you can't fix it.

### For backend bugs:
```bash
# Run the specific test or endpoint locally
TESTING=1 python -m uvicorn src.main:app --reload --log-level debug
curl -v http://localhost:8000/api/<endpoint>

# Or via smoke tests
TESTING=1 python -m pytest tests/test_api_smoke.py -k "test_name" -v --tb=long
```

### For frontend bugs:
```bash
# Fetch the live page and inspect the relevant JS/CSS
# Check browser console for errors
# Look at the specific component in static/js/<module>.js
```

### For live-site-only bugs:
```python
# Use requests through Intel proxy to hit the live site
import requests
proxies = {'https': 'http://proxy-dmz.intel.com:911'}
s = requests.Session()
s.proxies = proxies
r = s.get('https://investai-utho.onrender.com/api/<endpoint>')
print(r.status_code, r.text[:500])
```

**Output**: A clear statement of "I can reproduce this by doing X, expected Y, got Z."

If you **cannot** reproduce: document what you tried, ask the user for more details, check if it's environment-specific (mobile, screen size, specific browser).

## Phase 3: Diagnose

**Goal**: Find the root cause. Don't just fix the symptom.

1. **Trace the request path** — Follow `debugging.md` Step 3
2. **Read the code** — Don't guess; read the actual function that's failing
3. **Check recent changes** — `git log --oneline -10` — did a recent commit break this?
4. **Check if pre-existing** — Stash your changes, test on clean master:
   ```bash
   git stash
   # test the bug
   git stash pop
   ```

**Output**: "The root cause is X because Y" — one sentence.

## Phase 4: Fix

**Goal**: Write the smallest correct fix.

1. **Make the change** — Follow the coding rules in CLAUDE.md (no files >400 lines, user_id filtering, etc.)
2. **Run smoke tests locally**:
   ```bash
   TESTING=1 python -m pytest tests/test_api_smoke.py -v --tb=short
   ```
3. **If a test was already failing before your fix** — note it as pre-existing, don't block on it
4. **If you introduced a new test failure** — fix it before continuing

## Phase 5: Validate Locally

**Goal**: Confirm the fix actually works, not just that tests pass.

1. **Re-run the exact reproduction steps** from Phase 2
2. **Confirm the bug is gone** — same steps should now produce expected behavior
3. **Check for regressions** — test adjacent features that might be affected

## Phase 6: Deploy & Verify CI

**Goal**: Get the fix to production and confirm CI is green.

```bash
# 1. Commit with conventional commit message
git add -A
git commit -m "fix: concise description of what was broken and how it's fixed"

# 2. Ensure Intel proxy
git config --global http.proxy http://proxy-dmz.intel.com:911

# 3. Push
git push origin master
```

**4. VERIFY CI** (mandatory — do not skip):
- Fetch: https://github.com/MoS-ModelonSilicon/InvestAI/actions/workflows/pr-tests.yml
- Find the run matching your commit SHA
- Confirm: "completed successfully"
- If **failed**: read logs → fix → commit → push → re-check. Loop until green.

## Phase 7: Validate on Live Site

**Goal**: Confirm the fix works in production, not just locally.

1. **Wait for deploy** (~2 minutes after CI passes)
2. **Hit the live site**: https://investai-utho.onrender.com
3. **Reproduce the original bug steps on the live site** — it should now work correctly
4. **Document the result**: "Verified on live site — [feature] now works as expected"

### For frontend fixes:
- Hard-refresh (Ctrl+Shift+R) to bust browser cache
- Verify on the actual page where the bug was reported

### For backend fixes:
```python
# Hit the live endpoint through proxy
import requests
proxies = {'https': 'http://proxy-dmz.intel.com:911'}
s = requests.Session()
s.proxies = proxies
r = s.get('https://investai-utho.onrender.com/api/<fixed-endpoint>')
print(r.status_code, r.text[:500])
```

## Phase 8: Close

**Goal**: Record what happened for future reference.

1. **Add test coverage** — If the bug didn't have a test, add one to `tests/test_api_smoke.py`
2. **Update debugging docs** — If it's a new pattern, add a case study to `debugging.md`
3. **Update CLAUDE.md gotchas** — If it's a footgun, document it so it doesn't recur

## Mandatory Gates (NEVER skip)

| Gate | When | Blocks |
|------|------|--------|
| Reproduce bug | Before writing any fix | Phase 4 |
| Smoke tests pass locally | Before committing | Phase 6 |
| CI shows green | Before considering deployed | Phase 7 |
| Live site verification | Before considering done | Phase 8 |

**A bug is only CLOSED when all four gates have passed.**

## Quick Reference: Single-Line Checklist

```
[ ] Reproduced → [ ] Root cause identified → [ ] Fix written → [ ] Tests pass locally →
[ ] Committed & pushed → [ ] CI green → [ ] Verified on live site → [ ] Done
```

## Example: Bundle Modal Overflow Bug

1. **Report**: "Buy All popup is too large for screen, can't scroll to buttons"
2. **Reproduce**: Open Smart Advisor → Run Analysis → click Buy All → modal extends past viewport, Cancel/Add buttons hidden
3. **Diagnose**: `.bundle-modal` has no `max-height` on desktop; buttons are inside the scrollable body
4. **Fix**: Add `max-height: 80vh`, use flexbox with sticky header/footer, move buttons to `.bundle-footer`
5. **Validate locally**: Open modal with 15+ stocks → table scrolls, buttons always visible
6. **CI**: Commit `6c0cfdb` → CI Gate #24 → completed successfully
7. **Live site**: Verified at https://investai-utho.onrender.com — modal now scrolls properly
8. **Close**: CSS-only fix, no test needed; documented in this skill
