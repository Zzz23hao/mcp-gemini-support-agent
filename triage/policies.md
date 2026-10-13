# Contribution policies (read 2026-10-13)

Read from shallow clones of each default branch. Re-check before acting if this
file is more than a few weeks old.

| Repo | Commit read | Outside PRs accepted? | Gate | AI disclosure | CLA/DCO |
|------|-------------|-----------------------|------|---------------|---------|
| modelcontextprotocol/python-sdk | `c9356a2` (2026-10-12) | Yes, gated | Linked issue assigned to you, or labelled `help wanted` | Required | None found (MIT, contributions licensed under it) |
| googleapis/python-genai | `fa23221` (2026-10-12) | **No** | n/a | n/a | n/a |
| jlowin/fastmcp (now PrefectHQ/fastmcp) | `e2fcc41` (2026-10-08) | Yes, gated | Linked issue assigned to you, or labelled `prs welcome` | Allowed; you stay responsible | None found (Apache-2.0) |
| chroma-core/chroma | `5f30478` (2026-10-09) | Yes | None | No policy | None found (Apache-2.0) |

## modelcontextprotocol/python-sdk

Sources: `CONTRIBUTING.md`, `.github/pull_request_template.md`,
`.github/workflows/require-linked-issue.yml`, org-wide
`modelcontextprotocol/modelcontextprotocol/AI_POLICY.md`.

Gate:

> Pull requests from outside the maintainer team are only reviewed when a
> maintainer has assigned you the linked issue, and others are closed
> automatically.

> A PR from someone outside the maintainer team stays open when both of these hold:
> 1. Its description links an open issue in this repository with a closing keyword (`Fixes #123`, ...).
> 2. A maintainer has assigned that issue to you, or the issue carries the `help wanted` label

> `good first issue` still needs assignment — we'd like a short conversation first.

How to get assigned:

> Comments that only ask to be assigned don't factor into it, so please skip
> those (and don't have an agent post them). What does help is engaging with the
> issue itself: confirming the reproduction, asking about the intended
> behaviour, or briefly describing the approach you'd take.

> If you reported the issue and would like to fix it yourself, mention that in
> the issue — the reporter has first call if we do take an outside PR for it.

AI:

> **Disclose it.** One line in the PR description, issue, or comment.
> **Own it.** You can explain the change and the reasoning in your own words

Org policy adds: disclose "the extent to which AI assistance was used (e.g.,
documentation comments vs. code generation)". Example given: "I consulted
ChatGPT to understand the codebase but the solution was fully authored manually
by myself."

Needs an issue discussion first: new public APIs or decorators, architectural
changes, "Changes that touch multiple modules", anything needing a spec change.

Branch: `main` is v2 (target for fixes); `v1.x` takes only security and critical fixes.

Local checks: `uv sync --frozen --all-extras --dev`, `uv run pytest`,
`uv run pyright`, `uv run ruff check .`, `uv run ruff format .`.

PR template sections: `Fixes #`, Motivation and Context, How Has This Been
Tested?, Breaking Changes, Types of changes, Checklist (includes "I am assigned
to the linked issue" and "I have disclosed any AI assistance and can explain the
change in my own words"), Additional context.

## googleapis/python-genai

Source: `CONTRIBUTING.md`, in full:

> The Google Gen AI SDK will accept contributions in the future.

Evidence from history (last 300 commits on `main`): 272 carry a
`PiperOrigin-RevId` trailer (changes made inside Google and exported to GitHub).
The 11 commits imported from GitHub PRs (`COPYBARA_INTEGRATE_REVIEW`) all come
from `googleapis:` branches (release-please or a Googler's own branch). None
come from an outside fork. Core modules (`models.py`, `types.py`, `files.py`,
`caches.py`, `batches.py`, ...) carry a generated-code header.

Conclusion: not a PR target. A well-reproduced issue is the useful contribution here.

## jlowin/fastmcp (canonical: PrefectHQ/fastmcp)

Sources: `CONTRIBUTING.md`, `docs/development/contributing.mdx`,
`.github/pull_request_template.md`, `.github/workflows/require-issue-link.yml`.

Gate:

> External PRs must link an issue with an auto-close keyword such as
> `Fixes #123`. The author must also be assigned to that issue, unless it
> carries the `prs welcome` label.

> The issue reporter has first claim on implementing the fix; an open issue
> does not by itself mean a maintainer has accepted a proposed solution.

> Do not post comments just to claim an issue or ask to be assigned.

What is welcome:

> Simple, scoped bug fixes, documentation improvements, and authentication
> providers are welcome. Enhancements need a maintainer-approved design in an
> issue before implementation.

Competition:

> A separate triage agent may open draft fixes for unclaimed issues

AI:

> AI assistance is welcome under the same standards as other contributions. You
> remain responsible for understanding the change, verifying its behavior, and
> responding to review.

PR template checkbox: "If I used an LLM, it followed the repo's contributing
conventions (not generic output)". The guide also asks agents to read
`AGENTS.md` and the skills in `.agents/skills/`.

Tests: "For a bug fix, run the regression on unchanged code and confirm it fails
for the reported reason, then run it with the fix."

Local checks: `uv sync`, `uv run pytest -n auto`, `uv run prek run --all-files`.
"use a new commit rather than amending to repair a failed hook."

Layout: framework code lives in `fastmcp_slim/fastmcp/`; tests under `tests/`.

## chroma-core/chroma

Sources: `pull_request_template.md`, `docs/mintlify/docs/overview/oss.mdx`
(published as docs.trychroma.com contributing), `.github/workflows/pr-check-title.yml`.

> For smaller changes like bug fixes or documentation updates, you can submit
> an issue or open a pull request as usual.

PR title is enforced by CI with the regex
`\[(ENH|BUG|DOC|TST|BLD|PERF|TYP|CLN|CHORE|RELEASE|HOTFIX)\].*`, so the title
must start with e.g. `[BUG]`. (The docs page shows `BUG:` style; CI wants brackets.)

Priority note, relevant because our project uses local `PersistentClient`:

> Today, the majority of our engineering effort is focused on distributed
> Chroma and the cloud offering. As a result, local Chroma may temporarily lack
> some features or behaviors available in the distributed system.

PR template sections: Description of changes, Test plan ("Tests pass locally
with `pytest` for python, `yarn test` for js, `cargo test` for rust"), Migration
plan, Observability plan, Documentation Changes.

No AI policy, CLA or DCO found in the repository.
