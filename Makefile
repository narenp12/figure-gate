# One command per thing CI does, so that "run the audit" is a thing a person can
# do rather than a procedure they reconstruct from a workflow file.
#
# The audit had been run three times before this file existed, each time by
# reading the previous audit's changelog entry and redoing it from memory. That
# is how the second one missed `conda/recipe.yaml` as a version site and the
# third missed seven of the eleven prose documents: not because the checks were
# hard, but because the list of them lived in somebody's head.
#
# `specs/2026-07-30-standardized-docs-audit.md` is the long form: what each
# target proves, and what it deliberately does not.

.PHONY: audit audit-code audit-prose audit-docs audit-api audit-spelling test help

help:
	@echo "make audit          every check below, in the order a failure is cheapest to read"
	@echo "make audit-code     ruff and mypy, including the four docstring rules"
	@echo "make audit-prose    the markdown sweeps: claims, counts, tables, corpus"
	@echo "make audit-docs     the site builds strict, and every nav page exists"
	@echo "make audit-api      the public API against the last release tag"
	@echo "make audit-spelling codespell over prose and code"
	@echo "make test           the full suite"

# Ordered by how long each takes and how legible its failure is. Spelling and
# lint fail in seconds and name a line; the site build takes a minute and fails
# with a traceback. A contributor who runs this wants the cheap answer first.
audit: audit-spelling audit-code audit-prose audit-docs audit-api
	@echo
	@echo "Audit clean."

audit-spelling:
	uv run codespell

audit-code:
	uv run ruff check .
	uv run mypy

# The prose gates specifically, not the whole suite. These are the files that
# join a document to the code it describes, and running them alone is what makes
# a documentation change a fast edit-check loop rather than a full test run.
audit-prose:
	uv run pytest tests/test_prose_claims.py tests/test_docs_match_code.py \
		tests/test_docs_site.py tests/test_api_reference.py \
		tests/test_version_sites.py -q

# `--strict` is a CLI flag and not a setting: Zensical has no `strict` key, and
# a config carried over from MkDocs builds a site with a dangling page and exits
# 0. The flag belongs on every invocation, including this one.
audit-docs:
	uv run --only-group docs zensical build --strict

# Static, so it needs neither the project installed nor a network. It does need
# tags: a shallow clone has nothing to compare against and will say so.
audit-api:
	uv run --only-group api python skill/scripts/audit_api.py

test:
	uv run pytest tests/ -n auto -q
