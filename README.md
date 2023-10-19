# Marin3r End-to-End tests

This repository contains end-to-end tests for [Marin3r](https://github.com/3scale-ops/marin3r) project.

## Requirements

To run the testsuite you currently need an OpenShift 4.x cluster with Marin3r Operator deployed and namespace where the tests will be executed.

## Configuration

Marin3r tests uses [Dynaconf](https://www.dynaconf.com/) for configuration, which means you can specify the configuration through either settings files in `config` directory or through environmental variables. 
All the required and possible configuration options can be found in `config/settings.local.yaml.tpl`

### Settings files

Settings files are located at `config` directory and are in `yaml` format. To use them for local development, you can create `settings.local.yaml` and put all settings there.

### Environmental variables

You can also configure all the settings through environmental variables as well. We use prefix `MARIN3R` so the variables can look like this:
```bash
export MARIN3R_OPENSHIFT__project="test-project"
```
You can find more info on the [Dynaconf wiki page](https://www.dynaconf.com/envvars/)

## Usage

You can run and manage environment for testsuite with the included Makefile, but the recommended way how to run the testsuite is from Container image

### Local development setup

Requirements:
* Python 3.9+
* [poetry](https://python-poetry.org/)
* [CFSSL](https://github.com/cloudflare/cfssl)
* [OpenShift CLI tools](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html) (oc)

If you have all of those, you can run ```poetry install --no-root``` to install virtual environment and all dependencies
To run all tests you can then use ```make test```

### Running from container

For just running tests, the container image is the easiest option, you can log in to OpenShift and then run it like this

If you omit any options, Testsuite will run only subset of tests that don't require that variable e.g. not providing Auth0 will result in skipping Auth0 tests.

NOTE: For binding kubeconfig file, the "others" need to have permission to read, otherwise it will not work.
The results and reports will be saved in `/test-run-results` in the container.

#### With tools setup

```bash
podman run \
	-v $HOME/.kube/config:/run/kubeconfig:z \
	-e MARIN3R_OPENSHIFT__project=test-project \
	ghcr.io/3scale-qe/marin3r-tests:latest
```
