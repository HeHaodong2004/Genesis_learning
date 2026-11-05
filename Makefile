SHELL := /bin/bash
.DEFAULT_GOAL := help
PY := scripts/gnav-env.sh python

.PHONY: help doctor config test check lab lab-red
help:
	@printf '%s\n' 'Genesis developer workbench (no simulation)' '  make doctor  - inspect interpreter, source path and dependencies' '  make config  - validate and resolve an example configuration' '  make test    - run lightweight developer tests' '  make check   - run the local development gate' '  make lab     - verify the reference learning exercise' '  make lab-red - run the deliberately incomplete exercise (expected failure)'

doctor:
	@$(PY) developer/gnav_dev.py doctor

config:
	@$(PY) developer/gnav_dev.py config --config configs/eval.yaml backend=cpu env.n_envs=2

test:
	@$(PY) -m unittest discover -s developer/tests -v

check:
	@$(PY) developer/check.py

lab:
	@$(PY) -m unittest discover -s developer/labs -p 'test_*.py' -v

lab-red:
	@LAB_IMPLEMENTATION=starter $(PY) -m unittest discover -s developer/labs -p 'test_*.py' -v
