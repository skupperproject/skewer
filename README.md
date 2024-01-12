# Skewer

[![main](https://github.com/skupperproject/skewer/actions/workflows/main.yaml/badge.svg)](https://github.com/skupperproject/skewer/actions/workflows/main.yaml)

A library for documenting and testing Skupper examples

A `skewer.yaml` file describes the steps and commands to achieve an
objective using Skupper.  Skewer takes the `skewer.yaml` file as input
and produces two outputs: a `README.md` file and a test routine.

## An example example

[Example `skewer.yaml` file](test-example/skewer.yaml)

[Example `README.md` output](test-example/README.md)

## Setting up Skewer for your own example

**Note:** This is how you set things up from scratch.  You can also
use the [Skupper example template][template] as a starting point.

[template]: https://github.com/skupperproject/skupper-example-template

Add the Skewer code as a subdirectory in your example project:

    cd <project-dir>/
    mkdir external
    curl -sfL https://github.com/skupperproject/skewer/archive/main.tar.gz | tar -C external -xz

Symlink the Skewer library into your `python` directory:

    mkdir -p python
    ln -s ../external/skewer-main/python/skewer python/skewer

Symlink the `plano` command into the root of your project.  Symlink
the standard `config/.plano.py` as `.plano.py` in the root as well:

    ln -s external/skewer-main/plano
    ln -s external/skewer-main/config/.plano.py

<!-- This sucks.  GitHub Actions doesn't support workflow files as symlinks. -->

<!-- Symlink the standard GitHub Actions workflow file: -->

<!--     mkdir -p .github/workflows -->
<!--     ln -s ../../external/skewer-main/config/.github/workflows/main.yaml .github/workflows/main.yaml -->

<!-- So I have a convenience for copying the latest version into place. -->

To use the `./plano` command, you must have the Python `pyyaml`
package installed.  Use `pip` (or `pip3` on some systems) to install
it:

    pip install pyyaml

Use the `plano update-workflow` command to copy the latest GitHub
Actions workflow file into your project:

    ./plano update-workflow

Use your editor to create a `skewer.yaml` file in the root of your
project:

    emacs skewer.yaml

Run the `./plano` command to see the available commands:

~~~ console
$ ./plano
usage: plano [--verbose] [--quiet] [--debug] [-h] [-f FILE] [-m MODULE] {command} ...

Run commands defined as Python functions

options:
  --verbose             Print detailed logging to the console
  --quiet               Print no logging to the console
  --debug               Print debugging output to the console
  -h, --help            Show this help message and exit
  -f FILE, --file FILE  Load commands from FILE (default '.plano.py')
  -m MODULE, --module MODULE
                        Load commands from MODULE

commands:
  {command}
    generate            Generate README.md from the data in skewer.yaml
    render              Render README.html from the data in skewer.yaml
    clean               Clean up the source tree
    run                 Run the example steps using Minikube
    run-external        Run the example steps with user-provided kubeconfigs
    demo                Run the example steps and pause before cleaning up
    test                Test README generation and run the steps on Minikube
    update-workflow     Update the GitHub Actions workflow file
    update-skewer       Update the embedded Skewer repo
~~~

## Skewer YAML

The top level:

~~~ yaml
title:              # Your example's title (required)
subtitle:           # Your chosen subtitle (required)
github_actions_url: # The URL of your workflow (optional)
overview:           # Text introducing your example (optional)
prerequisites:      # Text describing prerequisites (optional, has default text)
sites:              # A map of named sites (see below)
steps:              # A list of steps (see below)
summary:            # Text to summarize what the user did (optional)
next_steps:         # Text linking to more examples (optional, has default text)
~~~

A **site**:

~~~ yaml
<site-name>:
  title:            # The site title (optional)
  platform:         # "kubernetes" or "podman" (required)
  namespace:        # The Kubernetes namespace (required for Kubernetes sites)
  env:              # A map of named environment variables
~~~

A tilde (~) in the kubeconfig file path is replaced with a temporary
working directory during testing.

Kubernetes sites must have a `KUBECONFIG` environment variable with a
path to a kubeconfig file.  Podman sites must have a
`SKUPPER_PLATFORM` variable with the value `podman`.

Example sites:

~~~ yaml
sites:
  east:
    title: East
    platform: kubernetes
    namespace: east
    env:
      KUBECONFIG: ~/.kube/config-east
  west:
    title: West
    platform: podman
    env:
      SKUPPER_PLATFORM: podman
~~~

A **step**:

~~~ yaml
- title:            # The step title (required)
  preamble:         # Text before the commands (optional)
  commands:         # Named groups of commands.  See below.
  postamble:        # Text after the commands (optional)
~~~

An example step:

~~~ yaml
steps:
  - title: Expose the frontend service
    preamble: |
      We have established connectivity between the two namespaces and
      made the backend in `east` available to the frontend in `west`.
      Before we can test the application, we need external access to
      the frontend.

      Use `kubectl expose` with `--type LoadBalancer` to open network
      access to the frontend service.  Use `kubectl get services` to
      check for the service and its external IP address.
    commands:
      east: <list-of-commands>
      west: <list-of-commands>
~~~

Or you can use a named step from the library of standard steps:

~~~ yaml
- standard: configure_separate_console_sessions
~~~

The standard steps are defined in
[python/standardsteps.yaml](python/standardsteps.yaml).  Note that you
should not edit this file.  Instead, in your `skewer.yaml` file, you
can create custom steps based on the standard steps.  You can override
the `title`, `preamble`, `commands`, or `postamble` field of a
standard step by adding the field in addition to `standard`:

~~~ yaml
- standard: cleaning_up
  commands:
    east:
     - run: skupper delete
     - run: kubectl delete deployment/database
    west:
     - run: skupper delete
~~~

The initial steps are usually standard ones.  There are also some
standard steps at the end.  You may be able to use something like
this:

~~~ yaml
steps:
  - standard: configure_separate_console_sessions
  - standard: access_your_clusters
  - standard: set_up_your_namespaces
  - standard: install_skupper_in_your_namespaces
  - standard: check_the_status_of_your_namespaces
  - standard: link_your_namespaces
  <your-custom-steps>
  - standard: test_the_application
  - standard: accessing_the_web_console
  - standard: cleaning_up
~~~

Note that the `link_your_namespaces` and `test_the_application` steps
are less generic than the other steps, so check that the text and
commands they produce are doing what you need.  If not, you'll need to
provide a custom step.

The step commands are separated into named groups corresponding to the
sites.  Each named group contains a list of command entries.  Each
command entry has a `run` field containing a shell command and other
fields for awaiting completion or providing sample output.

A **command**:

~~~ yaml
- run:              # A shell command (required)
  apply:            # Use this command only for "readme" or "test" (optional, default is both)
  output:           # Sample output to include in the README (optional)
~~~

Only the `run` and `output` fields are used in the README content.
The `output` field is used as sample output only, not for any kind of
testing.

The `apply` field is useful when you want the readme instructions to
be different from the test procedure, or you simply want to omit
something.

There are also some special "await" commands that you can use to pause
for a condition you require before going to the next step.  They are
used only for testing and do not impact the README.

~~~ yaml
- await_resource:     # A resource (as in, deployment/frontend) for which to await readiness (optional)
- await_external_ip:  # A service (as in, service/frontend) for which to await an external IP (optional)
- await_http_ok:      # A service and URL template (as in, service/frontend and "http://{}:8080/api/hello")
                      # for which to await an HTTP OK response (optional)
~~~

Example commands:

~~~ yaml
commands:
  east:
    - run: kubectl expose deployment/backend --port 8080 --type LoadBalancer
      output: |
        service/frontend exposed
  west:
    - await_resource: service/backend
    - run: kubectl get service/backend
      output: |
        NAME          TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)         AGE
        backend       ClusterIP      10.102.112.121   <none>           8080/TCP        30s
~~~

## Demo mode

Skewer has a mode where it executes all the steps, but before cleaning
up and exiting, it pauses so you can inspect things.

It is enabled by setting the environment variable `SKEWER_DEMO` to any
value when you call `./plano run` or one of its variants.  You can
also use `./plano demo`, which sets the variable for you.
