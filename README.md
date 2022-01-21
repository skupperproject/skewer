# Skewer

[![main](https://github.com/skupperproject/skewer/actions/workflows/main.yaml/badge.svg)](https://github.com/skupperproject/skewer/actions/workflows/main.yaml)

A library for documenting and testing Skupper examples

## An example example

[Example `skewer.yaml` file](test-example/skewer.yaml)

[Example `README.md` output](test-example/README.md)

[Example generate and test functions](test-example/Planofile)

## Setting up Skewer for your own example

Add the Skewer code as a subrepo in your project:

    cd project-dir/
    git subrepo clone https://github.com/skupperproject/skewer subrepos/skewer

Symlink the Skewer libraries into your `python` directory:

    mkdir -p python
    ln -s ../subrepos/skewer/python/skewer.strings python/skewer.strings
    ln -s ../subrepos/skewer/python/skewer.py python/skewer.py
    ln -s ../subrepos/skewer/python/plano.py python/plano.py

Symlink the `plano` command into the root of your project.  Copy the
example `Planofile` there as well:

    ln -s subrepos/skewer/subrepos/plano/bin/plano
    cp subrepos/skewer/test-example/Planofile Planofile

Use your editor to create a `skewer.yaml` file:

     emacs skewer.yaml

Run the `./plano` command to see what you can do: generate the
README.md and test your example.

     ./plano

## Installing Git Subrepo on Fedora

    dnf install git-subrepo

## Updating a Skewer subrepo inside your example project

Usually this will do what you want:

    git subrepo pull --force subrepos/skewer

If you made changes to the Skewer subrepo, the command above will ask
you to perform a merge.  You can use the procedure that the subrepo
tooling offers, but if you'd prefer to simply blow away your changes
and get the latest Skewer, you can use the following procedure:

    git subrepo clean subrepos/skewer
    git rm -rf subrepos/skewer/
    git commit -am "Temporarily remove the previous version of Skewer"
    git subrepo clone https://github.com/skupperproject/skewer subrepos/skewer

## Skewer YAML

The top level:

~~~ yaml
title:               # Your example's title (required)
subtitle:            # Your chosen subtitle (required)
github_actions_url:  # The URL of your workflow (optional)
overview:            # A block of Markdown text introducing your example (optional)
prerequisites: !string prerequisites
sites:               # A map of named sites.  See!
steps:               # A list of steps.  See!
summary:             # A block of Markdown to summarize what the user did (optional)
cleaning_up:
next_steps:
~~~

A site:

~~~ yaml
<site-name>:
  kubeconfig: <kubeconfig-file>  # (required)
  namespace: <namespace-name>    # (required)
~~~

A step:

~~~ yaml
title:      # (required)
preamble:   # (optional)
commands:   # (optional)
postamble:  # (optional)
~~~

An example step:

~~~ yaml
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
      west:
        - run: kubectl expose deployment/hello-world-frontend --port 8080 --type LoadBalancer
          await_external_ip: [service/hello-world-frontend]
          output: |
            service/hello-world-frontend exposed
        - run: kubectl get services
          output: |
            NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)                           AGE
            hello-world-backend    ClusterIP      10.102.112.121   <none>           8080/TCP                          30s
            hello-world-frontend   LoadBalancer   10.98.170.106    10.98.170.106    8080:30787/TCP                    2s
            skupper                LoadBalancer   10.101.101.208   10.101.101.208   8080:31494/TCP                    82s
            skupper-router         LoadBalancer   10.110.252.252   10.110.252.252   55671:32111/TCP,45671:31193/TCP   86s
            skupper-router-local   ClusterIP      10.96.123.13     <none>           5671/TCP                          86s
~~~

Or you can use a named, canned step from the library of standard
steps:

~~~ yaml
standard: configure_separate_console_sessions
~~~

The initial steps are usually standard ones, so you may be able to use
this:

~~~ yaml
steps:
  - standard: configure_separate_console_sessions
  - standard: access_your_clusters
  - standard: set_up_your_namespaces
  - standard: install_skupper_in_your_namespaces
  - standard: check_the_status_of_your_namespaces
  [...]
~~~
