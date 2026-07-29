#!/usr/bin/env python3
"""Stamp `recipe.yaml` with the version in pyproject.toml and PyPI's sha256.

Run it after the PyPI release for that version exists -- the hash is of the
sdist PyPI is serving, so there is nothing to read before then:

    uv run python conda/update_recipe.py

Stdlib only and no network beyond one urlopen, so it runs in a fresh checkout
without installing anything.
"""

import hashlib
import json
import re
import sys
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECIPE = ROOT / "conda" / "recipe.yaml"
PYPROJECT = ROOT / "pyproject.toml"

# The name PyPI serves the sdist under. hatchling normalises the hyphen to an
# underscore in the artifact filename but not in the project name, and the
# recipe's `source.url` has to spell both.
SDIST = "figure_gate-{version}.tar.gz"
PYPI_JSON = "https://pypi.org/pypi/figure-gate/json"


def project_version():
    return tomllib.loads(PYPROJECT.read_text())["project"]["version"]


def pypi_sdist(version):
    """The sdist's declared sha256, and the bytes it is a hash of.

    Both, on purpose: PyPI's `digests.sha256` is the value the recipe needs,
    but taking it on faith would put an unverified hash in a build recipe. The
    download is hashed and compared, so what gets stamped is a number this
    script computed.
    """
    with urllib.request.urlopen(PYPI_JSON, timeout=30) as response:
        payload = json.load(response)

    releases = payload.get("releases", {})
    if version not in releases:
        sys.exit(f"figure-gate {version} is not on PyPI yet -- run this after "
                 f"the release workflow finishes")

    wanted = SDIST.format(version=version)
    for artifact in releases[version]:
        if artifact["filename"] == wanted:
            break
    else:
        sys.exit(f"no sdist named {wanted} in the {version} release")

    with urllib.request.urlopen(artifact["url"], timeout=60) as response:
        digest = hashlib.sha256(response.read()).hexdigest()

    declared = artifact["digests"]["sha256"]
    if digest != declared:
        sys.exit(f"downloaded sdist hashes to {digest}, PyPI says {declared}")
    return digest


def stamp(text, version, sha256):
    text, versions = re.subn(r'(?m)^(  version: ").*(")$',
                             rf"\g<1>{version}\g<2>", text)
    text, hashes = re.subn(r"(?m)^(  sha256: ).*$",
                           rf"\g<1>{sha256}", text)
    if versions != 1 or hashes != 1:
        sys.exit(f"recipe.yaml no longer has exactly one version line and one "
                 f"sha256 line (found {versions} and {hashes})")
    return text


def main():
    version = project_version()
    sha256 = pypi_sdist(version)
    RECIPE.write_text(stamp(RECIPE.read_text(), version, sha256))
    print(f"recipe.yaml -> figure-gate {version}, sha256 {sha256}")


if __name__ == "__main__":
    main()
