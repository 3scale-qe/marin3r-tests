.PHONY: commit-acceptance pylint test black \

TB ?= short
LOGLEVEL ?= INFO

PYTEST = poetry run python -m pytest --tb=$(TB)

ifdef junit
PYTEST += --junitxml=$(resultsdir)/junit-$(@F).xml -o junit_suite_name=$(@F)
endif

ifdef html
PYTEST += --html=$(resultsdir)/report-$(@F).html
endif

commit-acceptance: black pylint all-is-package

pylint:
	poetry run $@ $(flags) testsuite

black: pipenv-dev
	poetry run black --line-length 120 --check testsuite --diff

all-is-package:
	@echo
	@echo "Searching for dirs missing __init__.py"
	@! find testsuite/ -type d \! -name __pycache__ \! -path 'testsuite/resources/*' \! -exec test -e {}/__init__.py \; -print | grep '^..*$$'

# pattern to run individual testfile or all testfiles in directory
testsuite/%: FORCE pipenv
	$(PYTEST) -v $(flags) $@

test: ## Run test
test pytest tests:
	$(PYTEST) --dist loadfile $(flags) testsuite

# Check http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## Print this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# this ensures dependent target is run everytime
FORCE:
