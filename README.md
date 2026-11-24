[![Pytest Tests](https://github.com/or-fusion/sparow/actions/workflows/pytest.yml/badge.svg?branch=main)](https://github.com/or-fusion/sparow/actions/workflows/pytest.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/or-fusion/sparow/branch/main/graph/badge.svg)](https://codecov.io/gh/or-fusion/sparow)
[![Documentation Status](https://readthedocs.org/projects/sparow/badge/?version=latest)](http://sparow.readthedocs.org/en/latest/)
[![GitHub contributors](https://img.shields.io/github/contributors/or-fusion/sparow.svg)](https://github.com/or-fusion/sparow/graphs/contributors)
[![Merged PRs](https://img.shields.io/github/issues-pr-closed-raw/or-fusion/sparow.svg?label=merged+PRs)](https://github.com/or-fusion/sparow/pulls?q=is:pr+is:merged)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# sparow

## Description

Sparow is a Python library of optimization solvers for stochastic
programming.

## Installation

Sparow requires the installation of or-topas, which can be installed using **pip** as follows:

```bash
git clone git@github.com:or-fusion/or_topas.git
cd or_topas
pip install -e .
cd ..
```

Developers should install Sparow using **pip** as follows:

```bash
git clone git@github.com:or-fusion/sparow.git
cd sparow
pip install -e .
cd ..
```

There are some shell scripts and plotting code located in `bin` that can be used for running numerical experiments with the Uncertainty Quantification (UQ) workflows. In these scripts, you can change the file paths to use your own custom stochastic programming models (see the `README.md` in `sparow/conf_intervals` for more details). If you want to run these optional plotting scripts that generate figures from results stored in CSV format, then install the plotting dependencies:

```bash
cd sparow
pip install -e ".[plot]"
cd ..
```

Additionally, the following syntax generates a summary that includes code coverage:

```bash
pytest --cov-report term-missing --cov=sparow .
```
