# Current Task: semantic-result-column-break

**Complexity:** Level 1

## Fix

* What broke: `9b1fd45` (`feat(semantic): include session and message ids in every result`) inserted `session_id` and `message_id` before `role` in the default `tsv` and `table` shapes. release-please opened pull request #134 as 1.3.0 from that `feat`.
* Why: the default header is the pipe contract. Field 4 was `role` and is now `session_id`. Stockroom is on 1.2.1, so that shift is a major bump. The product diff is already on `main` and is not being rewritten.
* What changed: empty commit `eb96053`, `chore(semantic)!: record the default result-column break`, with a `BREAKING CHANGE:` footer naming the new header. No product files changed.
* Files affected: none in the product tree. The commit is empty so release-please reads the message.
* Test: no new test. The change is a commit message, not executable behavior. A test that asserted on the message would only fail when someone edited that message.

## QA Results

* **Status:** PASS
* **Semantic Review Findings:**
    - **KISS/DRY/YAGNI:** Clean implementation using an empty conventional commit with `BREAKING CHANGE:` footer; no speculative code or unnecessary abstractions.
    - **Completeness:** Commit `eb96053` contains the exact conventional commit syntax and footer needed for release-please to bump the next release to 2.0.0. Pull request creation is ready to be executed upon wrap-up.
    - **Regression:** No product code modified; no regressions.
    - **Documentation/Integrity:** Commit message accurately documents the breaking change details and positional column shift (`rank, score, harness, session_id, message_id, role, preview`).
