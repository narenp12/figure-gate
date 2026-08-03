"""Every job in every workflow carries `timeout-minutes`.

A step that hangs is not a failure. GitHub's default is the six-hour job cap,
so an unbounded job that stalls holds a runner for six hours and reports
nothing but a spinner the whole time, and a hung `test` job in `release.yml`
holds the release with it. That is not hypothetical here: `test` in `ci.yml`
did it, on `sudo apt-get install texlive-xetex` against a stalled mirror.

The install was made retrying and bounded where it stood, and this file is the
part that keeps the answer. A timeout is one line, invisible once written, and
nothing about a green run says whether the next job added to these files has
one. The bound belongs to every job rather than to the one that hung.

Parsed by hand rather than with PyYAML, for the reason `test_conda_recipe.py`
gives at more length: the pytest job in CI installs matplotlib, pytest and
xdist and nothing else, so a test that imported a YAML library would skip in
the one place it most needs to run.
"""

import re

import pytest

from conftest import SCRIPTS

ROOT = SCRIPTS.parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))

# A workflow's `on:` block has two-space keys too (`push`, `schedule`), so the
# scan starts at `jobs:` rather than matching two-space keys anywhere.
JOB = re.compile(r"^  ([a-z][a-z0-9_-]*):$", re.M)


def jobs():
    """(workflow name, job id, the job's own lines) for every job defined."""
    found = []
    for path in WORKFLOWS:
        text = path.read_text()
        start = re.search(r"^jobs:$", text, re.M)
        assert start, f"{path.name} defines no `jobs:` block"
        body = text[start.end():]
        starts = [(m.group(1), m.start()) for m in JOB.finditer(body)]
        for i, (job_id, at) in enumerate(starts):
            end = starts[i + 1][1] if i + 1 < len(starts) else len(body)
            found.append((path.name, job_id, body[at:end]))
    return found


ALL_JOBS = jobs()


def test_the_scan_found_the_jobs():
    """The parametrised test below says nothing about jobs it cannot see.

    Five workflow files, fourteen jobs at the time of writing. The count is
    not asserted -- adding a job is normal and this file's whole point is that
    a new one is covered without anyone editing a test -- but zero, or one per
    file, means the scan stopped matching the shape of these files.
    """
    assert len(ALL_JOBS) >= len(WORKFLOWS), (
        f"found {len(ALL_JOBS)} jobs across {len(WORKFLOWS)} workflow files, "
        "which is fewer than one apiece: JOB no longer matches how these "
        "files declare a job, and every assertion below is vacuous")


@pytest.mark.parametrize(
    "workflow,job_id,body",
    ALL_JOBS,
    ids=[f"{name}:{job_id}" for name, job_id, _ in ALL_JOBS])
def test_a_job_is_bounded(workflow, job_id, body):
    match = re.search(r"^    timeout-minutes: (\d+)$", body, re.M)
    assert match, (
        f"{workflow}'s `{job_id}` job has no `timeout-minutes`, so a step "
        "that stalls rather than fails runs to GitHub's six-hour cap. Give it "
        "a bound a few times its real runtime.")
    minutes = int(match.group(1))
    assert 0 < minutes <= 60, (
        f"{workflow}'s `{job_id}` job is bounded at {minutes} minutes. "
        "Nothing in this repository takes an hour; a bound that loose is the "
        "six-hour cap with extra steps.")
