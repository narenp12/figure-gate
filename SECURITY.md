# Security

## Reporting a vulnerability

Report privately through GitHub, not in a public issue:
[**Report a vulnerability**](https://github.com/narenp12/figure-gate/security/advisories/new).

That opens a private advisory only you and the maintainer can read. If you
cannot use it, email <146764727+narenp12@users.noreply.github.com> with
`figure-gate security` in the subject line.

Expect a first reply within 7 days and a fix or an explanation of why it is not
one within 30. You will be credited in the advisory unless you ask not to be.

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | yes |
| < 0.1   | no |

Only the latest release gets fixes. The project is small enough that a patch
release is cheap and a backport branch would be pretense.

## What counts here

This is not a service and holds no data. It is three scripts that run inside
someone else's test suite or build, usually on figures that project wrote
itself. That narrows what a vulnerability actually looks like:

**In scope**

- Code execution, file writes or network access triggered by a palette string,
  a figure, or a command-line argument. Nothing here should reach outside the
  process, and `check_palette.py` imports nothing outside the standard library
  precisely so that claim stays checkable.
- Anything that makes an installed artifact differ from the tagged source — a
  compromised release workflow, a wheel whose contents do not match the tag, a
  broken PEP 740 attestation.
- A path traversal or unexpected write in the report and figure-saving helpers.
- Denial of service that is disproportionate to the input: a palette of a dozen
  colors or a normal figure that hangs or exhausts memory. The `O(n^2)` fallback
  in `check_overplotting` on a genuinely enormous scatter is a documented
  trade-off, not a vulnerability.

**Out of scope**

- A gate that passes a figure it should fail, or fails one it should pass. That
  is a correctness bug and belongs in a public issue — it is the kind of report
  the project most wants, just not through this channel.
- Vulnerabilities in matplotlib, NumPy or SciPy. Report those upstream; if one
  needs a version floor raised here, open an issue and say so.
- Running the checkers on figures or palettes from an untrusted source as if
  they were sandboxed. They are not a sandbox, and matplotlib is not either.

## What the project does on its own behalf

- Release workflows pin their actions by commit, not by tag, and publish through
  PyPI trusted publishing with attestations.
- CodeQL runs on every change to `main` and weekly.
- Dependabot proposes action and dev-dependency updates weekly.
