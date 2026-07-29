# Publishing figure-gate to conda

The target is conda-forge, so the install line is `conda install -c
conda-forge figure-gate` with no extra channel to add. That costs one manual
submission to [conda-forge/staged-recipes][staged] and then nothing: once the
feedstock exists, conda-forge's autotick bot watches PyPI and opens the version
bump itself on every subsequent release.

Nothing in this directory runs in CI. It is not a second release pipeline; it
is the recipe conda-forge builds, kept in the repo so it can be reviewed and
held to `pyproject.toml` by `tests/test_conda_recipe.py`.

[staged]: https://github.com/conda-forge/staged-recipes

## First release: the one-time submission

The recipe pins its `source.url` to a PyPI sdist, so PyPI has to go first.

1. Cut the release as usual. `.github/workflows/release.yml` runs on the tag
   and puts the sdist on PyPI.
2. Stamp the recipe with that version and the hash of the sdist PyPI is
   actually serving:

   ```bash
   uv run python conda/update_recipe.py
   ```

   It downloads the sdist, hashes it, and checks the result against PyPI's
   declared digest before writing anything. It exits non-zero if the version in
   `pyproject.toml` is not on PyPI yet.
3. Commit the stamped `conda/recipe.yaml`.
4. Fork [conda-forge/staged-recipes][staged], copy the stamped file to
   `recipes/figure-gate/recipe.yaml` on a branch, and open a PR titled
   `Add figure-gate`. One recipe per PR.
5. Optional but worth it -- build it locally before asking a reviewer to:

   ```bash
   pixi exec rattler-build build --recipe conda/recipe.yaml
   ```

6. A conda-forge reviewer merges it, a bot creates
   `conda-forge/figure-gate-feedstock`, and the package appears on the
   `conda-forge` channel within an hour or so. `narenp12` is listed under
   `recipe-maintainers`, which is what grants write access to that feedstock.

## Every release after that

Nothing, in the normal case. The autotick bot opens a PR on the feedstock
within a day of the PyPI release; merge it once its CI is green.

Do it by hand only when the bot cannot: a changed dependency, a changed Python
floor, or a changed entry point. Those live in the feedstock's `recipe/`
directory, and the change is the same one made here -- keep the two in step,
because `conda/recipe.yaml` in this repo is what the next reader will believe.

## What the tests hold

`tests/test_conda_recipe.py` checks the recipe against `pyproject.toml` for the
three things that drift silently and are only discovered by a user whose
`conda install` produced something the `pip install` would not have:

- the recipe version equals the project version,
- the runtime dependencies and the Python floor match, allowing for
  conda-forge's `matplotlib-base` in place of PyPI's `matplotlib`,
- the entry points match `[project.scripts]`.

It deliberately does not check `sha256`, which is unknowable until the release
exists and is the one field `update_recipe.py` is responsible for.
