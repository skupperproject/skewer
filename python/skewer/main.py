#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

from plano import *

__all__ = [
    "generate_readme", "run_steps_minikube", "run_steps", "Minikube",
]

standard_steps_yaml = read(join(get_parent_dir(__file__), "standardsteps.yaml"))
standard_steps = parse_yaml(standard_steps_yaml)

example_suite_para = """
This example is part of a [suite of examples][examples] showing the
different ways you can use [Skupper][website] to connect services
across cloud providers, data centers, and edge sites.

[website]: https://skupper.io/
[examples]: https://skupper.io/examples/index.html
""".strip()

standard_prerequisites = """
* The `kubectl` command-line tool, version 1.15 or later
  ([installation guide][install-kubectl])

* Access to at least one Kubernetes cluster, from [any provider you
  choose][kube-providers]

[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[kube-providers]: https://skupper.io/start/kubernetes.html
""".strip()

standard_next_steps = """
Check out the other [examples][examples] on the Skupper website.
""".strip()

about_this_example = """
This example was produced using [Skewer][skewer], a library for
documenting and testing Skupper examples.

[skewer]: https://github.com/skupperproject/skewer

Skewer provides utility functions for generating the README and
running the example steps.  Use the `./plano` command in the project
root to see what is available.

To quickly stand up the example using Minikube, try the `./plano demo`
command.
""".strip()

def check_environment():
    check_program("base64")
    check_program("curl")
    check_program("kubectl")
    check_program("skupper")

# Eventually Kubernetes will make this nicer:
# https://github.com/kubernetes/kubernetes/pull/87399
# https://github.com/kubernetes/kubernetes/issues/80828
# https://github.com/kubernetes/kubernetes/issues/83094
def await_resource(resource, timeout=240):
    assert "/" in resource, resource

    start_time = get_time()

    while True:
        notice(f"Waiting for {resource} to become available")

        if run(f"kubectl get {resource}", output=DEVNULL, check=False, quiet=True).exit_code == 0:
            break

        if get_time() - start_time > timeout:
            fail(f"Timed out waiting for {resource}")

        sleep(5, quiet=True)

    if resource.startswith("deployment/"):
        try:
            run(f"kubectl wait --for condition=available --timeout {timeout}s {resource}", quiet=True, stash=True)
        except:
            run(f"kubectl logs {resource}")
            raise

def await_external_ip(service, timeout=240):
    assert service.startswith("service/"), service

    start_time = get_time()

    await_resource(service, timeout=timeout)

    while True:
        notice(f"Waiting for external IP from {service} to become available")

        if call(f"kubectl get {service} -o jsonpath='{{.status.loadBalancer.ingress}}'", quiet=True) != "":
            break

        if get_time() - start_time > timeout:
            fail(f"Timed out waiting for external IP for {service}")

        sleep(5, quiet=True)

    return call(f"kubectl get {service} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'", quiet=True)

def await_http_ok(service, url_template, user=None, password=None, timeout=240):
    assert service.startswith("service/"), service

    start_time = get_time()

    ip = await_external_ip(service, timeout=timeout)
    url = url_template.format(ip)
    insecure = url.startswith("https")

    while True:
        notice(f"Waiting for HTTP OK from {url}")

        try:
            http_get(url, insecure=insecure, user=user, password=password)
        except PlanoError:
            if get_time() - start_time > timeout:
                fail(f"Timed out waiting for HTTP OK from {url}")

            sleep(5, quiet=True)
        else:
            break

def await_console_ok():
    password = call("kubectl get secret/skupper-console-users -o jsonpath={.data.admin}", quiet=True)
    password = base64_decode(password)

    await_http_ok("service/skupper", "https://{}:8010/", user="admin", password=password)

def run_steps_minikube(skewer_file, debug=False):
    notice("Running steps on Minikube")

    check_environment()
    check_program("minikube")

    model = Model(skewer_file)
    model.check()

    kube_sites = [x for x in model.sites if x.platform == "kubernetes"]
    kubeconfigs = list()

    make_dir("/tmp/skewer", quiet=True)

    with Minikube():
        for site in kube_sites:
            kubeconfig = site.env["KUBECONFIG"].replace("~", "/tmp/skewer")
            site.env["KUBECONFIG"] = kubeconfig

            kubeconfigs.append(kubeconfig)

            with site:
                run("minikube -p skewer update-context")
                check_file(ENV["KUBECONFIG"])

        run_steps(skewer_file, kubeconfigs=kubeconfigs, debug=debug)

def run_steps(skewer_file, kubeconfigs=[], debug=False):
    notice(f"Running steps (skewer_file='{skewer_file}')")

    check_environment()

    model = Model(skewer_file, kubeconfigs)
    model.check()

    try:
        for step in model.steps:
            if step.name == "cleaning_up":
                continue

            run_step(model, step)

        if "SKEWER_DEMO" in ENV:
            pause_for_demo(model)
    except:
        if debug:
            print_debug_output(model)

        raise
    finally:
        for step in model.steps:
            if step.name == "cleaning_up":
                run_step(model, step, check=False)
                break

def run_step(model, step, check=True):
    if not step.commands:
        return

    notice(f"Running {step}")

    for site_name, commands in step.commands.items():
        with model.site(site_name) as site:
            if site.platform == "kubernetes":
                run(f"kubectl config set-context --current --namespace {site.namespace}", stdout=DEVNULL, quiet=True)

            for command in commands:
                if command.get("apply") == "readme":
                    continue

                if "run" in command:
                    make_dir("/tmp/skewer", quiet=True)
                    run(command["run"].replace("~", "/tmp/skewer"), shell=True, check=check)

                if "await_resource" in command:
                    resource = command["await_resource"]
                    await_resource(resource)

                if "await_external_ip" in command:
                    service = command["await_external_ip"]
                    await_external_ip(service)

                if "await_http_ok" in command:
                    service, url_template = command["await_http_ok"]
                    await_http_ok(service, url_template)

                if "await_console_ok" in command:
                    await_console_ok()

def pause_for_demo(model):
    notice("Pausing for demo time")

    first_site = list(model.sites)[0]
    frontend_url = None

    if first_site.platform == "kubernetes":
        with first_site:
            console_ip = await_external_ip("service/skupper")
            console_url = f"https://{console_ip}:8010/"

            # XXX Make this conditional on the console being present
            await_resource("secret/skupper-console-users")
            password_data = call("kubectl get secret/skupper-console-users -o jsonpath='{.data.admin}'", quiet=True)
            password = base64_decode(password_data).decode("ascii")

            if run("kubectl get service/frontend", check=False, output=DEVNULL, quiet=True).exit_code == 0:
                if call("kubectl get service/frontend -o jsonpath='{.spec.type}'", quiet=True) == "LoadBalancer":
                    frontend_ip = await_external_ip("service/frontend")
                    frontend_url = f"http://{frontend_ip}:8080/"

    print()
    print("Demo time!")
    print()
    print("Sites:")

    for site in model.sites:
        if site.platform == "kubernetes":
            kubeconfig = site.env["KUBECONFIG"]
            print(f"  {site.name}: export KUBECONFIG={kubeconfig}")

    if frontend_url:
        print()
        print(f"Frontend URL:     {frontend_url}")

    print()
    print(f"Console URL:      {console_url}")
    print( "Console user:     admin")
    print(f"Console password: {password}")
    print()

    if "SKEWER_DEMO_NO_WAIT" not in ENV:
        while input("Are you done (yes)? ") != "yes": # pragma: nocover
            pass

def print_debug_output(model):
    print("TROUBLE!")
    print("-- Start of debug output")

    for site in model.sites:
        print(f"---- Debug output for site '{site.name}'")

        with site:
            if site.platform == "kubernetes":
                run("kubectl get services", check=False)
                run("kubectl get deployments", check=False)
                run("kubectl get statefulsets", check=False)
                run("kubectl get pods", check=False)
                run("kubectl get events", check=False)

            run("skupper version", check=False)
            run("skupper status", check=False)
            run("skupper link status", check=False)
            run("skupper service status", check=False)
            run("skupper network status", check=False)
            run("skupper debug events", check=False)

            if site.platform == "kubernetes":
                run("kubectl logs deployment/skupper-router", check=False)
                run("kubectl logs deployment/skupper-service-controller", check=False)

    print("-- End of debug output")

def generate_readme(skewer_file, output_file):
    notice(f"Generating the readme (skewer_file='{skewer_file}', output_file='{output_file}')")

    model = Model(skewer_file)
    model.check()

    out = list()

    def append_toc_entry(title, condition=True):
        if not condition:
            return

        fragment = replace(title, r"[ -]", "_")
        fragment = replace(fragment, r"[\W]", "")
        fragment = replace(fragment, "_", "-")
        fragment = fragment.lower()

        out.append(f"* [{title}](#{fragment})")

    def append_section(heading, text):
        if not text:
            return

        out.append(f"## {heading}")
        out.append("")
        out.append(text.strip())
        out.append("")

    def step_heading(step):
        if step.numbered:
            return f"Step {step.number}: {step.title}"
        else:
            return step.title

    out.append(f"# {model.title}")
    out.append("")

    if model.github_actions_url:
        out.append(f"[![main]({model.github_actions_url}/badge.svg)]({model.github_actions_url})")
        out.append("")

    if model.subtitle:
        out.append(f"#### {model.subtitle}")
        out.append("")

    out.append(example_suite_para)
    out.append("")
    out.append("#### Contents")
    out.append("")

    append_toc_entry("Overview", model.overview)
    append_toc_entry("Prerequisites")

    for step in model.steps:
        append_toc_entry(step_heading(step))

    append_toc_entry("Summary")
    append_toc_entry("Next steps")
    append_toc_entry("About this example")

    out.append("")

    append_section("Overview", model.overview)
    append_section("Prerequisites", model.prerequisites)

    for step in model.steps:
        notice(f"Generating {step}")

        heading = step_heading(step)
        text = generate_readme_step(model, step)

        append_section(heading, text)

    append_section("Summary", model.summary)
    append_section("Next steps", model.next_steps)
    append_section("About this example", about_this_example)

    write(output_file, "\n".join(out).strip() + "\n")

def generate_readme_step(model, step):
    out = list()

    if step.preamble:
        out.append(step.preamble.strip())
        out.append("")

    if step.commands:
        for site_name, commands in step.commands.items():
            site = model.site(site_name)
            outputs = list()

            out.append(f"_**Console for {site.title}:**_")
            out.append("")
            out.append("~~~ shell")

            for command in commands:
                if command.get("apply") == "test":
                    continue

                if "run" in command:
                    out.append(command["run"])

                if "output" in command:
                    assert "run" in command, command

                    outputs.append((command["run"], command["output"]))

            out.append("~~~")
            out.append("")

            if outputs:
                out.append("_Sample output:_")
                out.append("")
                out.append("~~~ console")
                out.append("\n\n".join((f"$ {run}\n{output.strip()}" for run, output in outputs)))
                out.append("~~~")
                out.append("")

    if step.postamble:
        out.append(step.postamble.strip())

    return "\n".join(out).strip()

def apply_kubeconfigs(model, kubeconfigs):
    kube_sites = [x for x in model.sites if x.platform == "kubernetes"]

    for site, kubeconfig in zip(kube_sites, kubeconfigs):
        site.env["KUBECONFIG"] = kubeconfig

    notice(f"Applied kubeconfigs to {len(kubeconfigs)} of {len(kube_sites)} Kubernetes sites")

def apply_standard_steps(model):
    notice("Applying standard steps")

    for step in model.steps:
        if "standard" not in step.data:
            continue

        standard_step_data = standard_steps[step.data["standard"]]

        def apply_attribute(name, default=None):
            if name not in step.data:
                step.data[name] = standard_step_data.get(name, default)

        apply_attribute("name")
        apply_attribute("title")
        apply_attribute("numbered", True)
        apply_attribute("preamble")
        apply_attribute("postamble")

        if "commands" not in step.data:
            if "commands" in standard_step_data:
                step.data["commands"] = dict()

                for i, site_item in enumerate(model.data["sites"].items()):
                    site_name, site = site_item

                    if str(i) in standard_step_data["commands"]:
                        # Is a specific index in the standard commands?
                        commands = standard_step_data["commands"][str(i)]
                        step.data["commands"][site_name] = resolve_commands(commands, site)
                    elif "*" in standard_step_data["commands"]:
                        # Is "*" in the standard commands?
                        commands = standard_step_data["commands"]["*"]
                        step.data["commands"][site_name] = resolve_commands(commands, site)
                    else:
                        # Otherwise, omit commands for this site
                        continue

def resolve_commands(commands, site):
    resolved_commands = list()

    for command in commands:
        resolved_command = dict(command)

        if "run" in command:
            resolved_command["run"] = command["run"]

            if site["platform"] == "kubernetes":
                resolved_command["run"] = resolved_command["run"].replace("@kubeconfig@", site["env"]["KUBECONFIG"])
                resolved_command["run"] = resolved_command["run"].replace("@namespace@", site["namespace"])

        if "output" in command:
            resolved_command["output"] = command["output"]

            if site["platform"] == "kubernetes":
                resolved_command["output"] = resolved_command["output"].replace("@kubeconfig@", site["env"]["KUBECONFIG"])
                resolved_command["output"] = resolved_command["output"].replace("@namespace@", site["namespace"])

        resolved_commands.append(resolved_command)

    return resolved_commands

def object_property(name, default=None):
    def get(obj):
        return obj.data.get(name, default)

    return property(get)

def check_attribute(obj, name):
    if name not in obj.data:
        fail(f"{obj} has no '{name}' attribute")

known_command_fields = (
    "run", "apply", "output", "await_resource", "await_external_ip", "await_http_ok", "await_console_ok"
)

class Model:
    title = object_property("title")
    subtitle = object_property("subtitle")
    github_actions_url = object_property("github_actions_url")
    overview = object_property("overview")
    prerequisites = object_property("prerequisites", standard_prerequisites)
    summary = object_property("summary")
    next_steps = object_property("next_steps", standard_next_steps)

    def __init__(self, skewer_file, kubeconfigs=[]):
        self.skewer_file = skewer_file
        self.data = read_yaml(self.skewer_file)

        apply_kubeconfigs(self, kubeconfigs)
        apply_standard_steps(self)

    def __repr__(self):
        return f"model '{self.skewer_file}'"

    def check(self):
        check_attribute(self, "title")
        check_attribute(self, "subtitle")
        check_attribute(self, "sites")
        check_attribute(self, "steps")

        for site in self.sites:
            site.check()

        for step in self.steps:
            step.check()

    @property
    def sites(self):
        for name, data in self.data["sites"].items():
            yield Site(self, data, name)

    @property
    def steps(self):
        for data in self.data["steps"]:
            yield Step(self, data)

    def site(self, name):
        data = self.data["sites"][name]
        return Site(self, data, name)

class Site:
    platform = object_property("platform")
    namespace = object_property("namespace")
    env = object_property("env", dict())

    def __init__(self, model, data, name):
        assert name is not None

        self.model = model
        self.data = data
        self.name = name

    def __repr__(self):
        return f"site '{self.name}'"

    def __enter__(self):
        self._logging_context = logging_context(self.name)
        self._working_env = working_env(**self.env)

        self._logging_context.__enter__()
        self._working_env.__enter__()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._working_env.__exit__(exc_type, exc_value, traceback)
        self._logging_context.__exit__(exc_type, exc_value, traceback)

    def check(self):
        check_attribute(self, "platform")

        if self.platform not in ("kubernetes", "podman"):
            fail(f"{self} attribute 'platform' has an illegal value: {self.platform}")

        if self.platform == "kubernetes":
            check_attribute(self, "namespace")

            if "KUBECONFIG" not in self.env:
                fail(f"Kubernetes {self} has no KUBECONFIG environment variable")

        if self.platform == "podman":
            if "SKUPPER_PLATFORM" not in self.env:
                fail(f"Podman {self} has no SKUPPER_PLATFORM environment variable")

            platform = self.env["SKUPPER_PLATFORM"]

            if platform != "podman":
                fail(f"Podman {self} environment variable SKUPPER_PLATFORM has an illegal value: {platform}")

    @property
    def title(self):
        return self.data.get("title", capitalize(self.name))

class Step:
    numbered = object_property("numbered", True)
    name = object_property("name")
    title = object_property("title")
    preamble = object_property("preamble")
    commands = object_property("commands", dict())
    postamble = object_property("postamble")

    def __init__(self, model, data):
        self.model = model
        self.data = data

    def __repr__(self):
        return f"step {self.number} '{self.title}'"

    def check(self):
        check_attribute(self, "title")

        site_names = [x.name for x in self.model.sites]

        for site_name, commands in self.commands.items():
            if site_name not in site_names:
                fail(f"Unknown site name '{site_name}' in commands for {self}")

            for command in commands:
                for field in command:
                    if field not in known_command_fields:
                        fail(f"Unknown field '{field}' in command for {self}")

    @property
    def number(self):
        return self.model.data["steps"].index(self.data) + 1

class Minikube:
    def __enter__(self):
        check_program("minikube")

        run("minikube -p skewer start --auto-update-drivers false")

        make_dir("/tmp/skewer", quiet=True)
        tunnel_output_file = open("/tmp/skewer/minikube-tunnel-output", "w")

        self.tunnel = start("minikube -p skewer tunnel", output=tunnel_output_file)

    def __exit__(self, exc_type, exc_value, traceback):
        stop(self.tunnel)

        run("minikube -p skewer delete")
