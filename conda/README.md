# Publishing figure-gate to conda

The target is conda-forge, so the install line is `conda install -c
conda-forge figure-gate` with no extra channel to add. That cost one manual
submission to [conda-forge/staged-recipes][staged] and then nothing: the
feedstock exists now, and conda-forge's autotick bot watches PyPI and opens the
version bump itself on every subsequent release.

Nothing in this directory runs in CI. It is not a second release pipeline; it
is the recipe conda-forge started from, kept in the repo so it can be reviewed
and held to `pyproject.toml` by `tests/test_conda_recipe.py`.

[staged]: https://github.com/conda-forge/staged-recipes
[feedstock]: https://github.com/conda-forge/figure-gate-feedstock

## Where the package actually comes from

[`conda-forge/figure-gate-feedstock`][feedstock], created 2026-07-30 from the
0.4.0 recipe. **That repository's `recipe/recipe.yaml` is what gets built**, not
this one. `narenp12` is listed under `recipe-maintainers`, which grants write
access to the feedstock; it does not change how an update is produced, only who
can merge one.

The two copies can drift, and the tests here cannot see it: they hold
`conda/recipe.yaml` to `pyproject.toml`, and know nothing about the feedstock.
A changed dependency, Python floor or entry point has to be made in both, and
the feedstock is the copy that decides what users install.

## Every release

Nothing, in the normal case. `regro-cf-autotick-bot` polls PyPI on a loop and
opens a PR on the feedstock bumping `version` and `sha256` and resetting the
build number; merge it once its CI is green. It can take several hours after
the PyPI release, so a bump that has not appeared yet is usually not a problem.

Three things worth knowing:

- **The bot stops opening version PRs once three are open on the feedstock**, so
  an unmerged bump blocks later ones. Merge or close them.
- **To ask for the bump now**, open an issue on the feedstock with
  `@conda-forge-admin, please update version` as the title or body.
- **To stop merging them by hand**, open an issue with
  `@conda-forge-admin, please add bot automerge`. The admin bot opens a PR
  wiring it up, and after that a passing autotick PR merges itself. This package
  is `noarch: python` with two runtime dependencies, so there is not much for a
  human to review in a version bump.

Do it by hand only when the bot cannot: a changed dependency, a changed Python
floor, or a changed entry point. Those live in the feedstock's `recipe/`
directory, and the change is the same one made here.

## What `update_recipe.py` is for

The recipe pins its `source.url` to a PyPI sdist, so the hash cannot be written
until the release exists:

```bash
uv run python conda/update_recipe.py
```

It downloads the sdist, hashes it, and checks the result against PyPI's
declared digest before writing anything. It exits non-zero if the version in
`pyproject.toml` is not on PyPI yet.

Now that the feedstock exists, this keeps the in-repo copy honest rather than
feeding a submission -- the bot writes the feedstock's own hash. `version` in
this file moves with the release, because `bump-my-version` lists it (see
"Cutting a release" in `CONTRIBUTING.md`); `sha256` is the one field left to
this script.

## How the feedstock was created

Kept for the record, and for anyone repeating it with another package. The
recipe was stamped with `update_recipe.py` and committed, then:

1. Fork [conda-forge/staged-recipes][staged], copy the stamped file to
   `recipes/figure-gate/recipe.yaml` on a branch, and commit. One recipe per
   PR.
2. Lint and build it there, before asking a reviewer to. Both are tasks in
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
3. Open the PR, titled `Add figure-gate`. Post a comment confirming you are
   willing to be listed as a maintainer -- their checklist requires it and
   nobody else can post it for you. A first-time contributor cannot ping the
   review team directly, so ask the bot:
   `@conda-forge-admin, please ping conda-forge/help-python`.
4. A conda-forge reviewer merges it, a bot creates the feedstock, and the
   package appears on the `conda-forge` channel within an hour or so.

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
exists and is the one field `update_recipe.py` is responsible for. It does not
check the feedstock either: that is a different repository, and it is the one
that builds.
