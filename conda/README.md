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
   `recipes/figure-gate/recipe.yaml` on a branch, and commit. One recipe per
   PR.
5. Lint and build it there, before asking a reviewer to. Both are tasks in
   their `pixi.toml`, and running them rather than `rattler-build` directly is
   what exercises their variant config:

   ```bash
   pixi run lint && pixi run build-osx osx_arm64
   ```

   Three things that stop the build before it starts, none of them the
   recipe's fault: their workspace needs pixi >= 0.59 (`pixi self-update`), the
   script refuses to run on `main`, and `OSX_SDK_DIR` points at
   `.pixi/macOS-SDKs`, which has to exist or its writability probe aborts. The
   build also `rm -rf`s every recipe already in their `main` to isolate yours,
   so `git checkout -- .ci_support recipes` afterwards.
6. Open the PR, titled `Add figure-gate`. Post a comment confirming you are
   willing to be listed as a maintainer -- their checklist requires it and
   nobody else can post it for you. A first-time contributor cannot ping the
   review team directly, so ask the bot:
   `@conda-forge-admin, please ping conda-forge/help-python`.
7. A conda-forge reviewer merges it, a bot creates
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
things that drift silently and are only discovered by a user whose `conda
install` produced something the `pip install` would not have:

- the recipe version equals the project version,
- `source.url` interpolates that version rather than hard-coding one, so the
  test above cannot pass while the recipe fetches a different sdist,
- the runtime dependencies match, allowing for conda-forge's `matplotlib-base`
  in place of PyPI's `matplotlib`,
- the Python floor matches, in both `host` and `run`,
- the entry points match `[project.scripts]`.

`${{ }}` context variables are resolved before comparing, so `python
>=${{ python_min }}` is checked as the version it expands to.

It deliberately does not check `sha256`, which is unknowable until the release
exists and is the one field `update_recipe.py` is responsible for.
