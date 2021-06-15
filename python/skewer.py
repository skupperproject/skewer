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

import yaml as _yaml

def check_environment():
    check_program("kubectl")
    check_program("skupper")

# Eventually Kubernetes will make this nicer:
# https://github.com/kubernetes/kubernetes/pull/87399
# https://github.com/kubernetes/kubernetes/issues/80828
# https://github.com/kubernetes/kubernetes/issues/83094
def await_resource(group, name, namespace=None):
    base_command = "kubectl"

    if namespace is not None:
        base_command = f"{base_command} -n {namespace}"

    notice(f"Waiting for {group}/{name} to become available")

    for i in range(180):
        sleep(1)

        if run(f"{base_command} get {group}/{name}", check=False).exit_code == 0:
            break
    else:
        fail(f"Timed out waiting for {group}/{name}")

    if group == "deployment":
        try:
            run(f"{base_command} wait --for condition=available --timeout 180s {group}/{name}")
        except:
            run(f"{base_command} logs {group}/{name}")
            raise

def await_external_ip(group, name, namespace=None):
    await_resource(group, name, namespace=namespace)

    base_command = "kubectl"

    if namespace is not None:
        base_command = f"{base_command} -n {namespace}"

    for i in range(180):
        sleep(1)

        if call(f"{base_command} get {group}/{name} -o jsonpath='{{.status.loadBalancer.ingress}}'") != "":
            break
    else:
        fail(f"Timed out waiting for external IP for {group}/{name}")

def run_steps_on_minikube(skewer_file):
    with open(skewer_file) as file:
        skewer_data = _yaml.safe_load(file)

    work_dir = make_temp_dir()

    try:
        run("minikube -p skewer start")

        contexts = skewer_data["contexts"]

        for name, value in contexts.items():
            kubeconfig = value["kubeconfig"].replace("~", work_dir)

            with working_env(KUBECONFIG=kubeconfig):
                run("minikube -p skewer update-context")
                check_file(ENV["KUBECONFIG"])

        with open("/tmp/minikube-tunnel-output", "w") as tunnel_output_file:
            with start("minikube -p skewer tunnel", output=tunnel_output_file):
                execute_steps(work_dir, skewer_data)
    finally:
        run("minikube -p skewer delete")

def run_steps_external(skewer_file, **kubeconfigs):
    with open(skewer_file) as file:
        skewer_data = _yaml.safe_load(file)

    work_dir = make_temp_dir()
    contexts = skewer_data["contexts"]

    for name, kubeconfig in kubeconfigs.items():
        contexts[name]["kubeconfig"] = kubeconfig

    execute_steps(work_dir, skewer_data)

def execute_steps(work_dir, skewer_data):
    contexts = skewer_data["contexts"]

    for step_data in skewer_data["steps"]:
        if "commands" not in step_data:
            continue

        for context_name, commands in step_data["commands"].items():
            kubeconfig = contexts[context_name]["kubeconfig"].replace("~", work_dir)

            with working_env(KUBECONFIG=kubeconfig):
                for command in commands:
                    run(command["run"].replace("~", work_dir), shell=True)

                    if "await" in command:
                        for resource in command["await"]:
                            group, name = resource.split("/", 1)
                            await_resource(group, name)

                    if "await_external_ip" in command:
                        for resource in command["await_external_ip"]:
                            group, name = resource.split("/", 1)
                            await_external_ip(group, name)

                    if "sleep" in command:
                        sleep(command["sleep"])

def generate_readme(skewer_file, output_file):
    with open(skewer_file) as file:
        skewer_data = _yaml.safe_load(file)

    out = list()

    out.append(f"# {skewer_data['title']}")
    out.append("")

    if "github_actions_url" in skewer_data:
        url = skewer_data["github_actions_url"]
        out.append(f"[![main]({url}/badge.svg)]({url})")
        out.append("")

    if "subtitle" in skewer_data:
        out.append(f"#### {skewer_data['subtitle']}")
        out.append("")

    out.append(_strings["example_suite_para"])
    out.append("")
    out.append("#### Contents")
    out.append("")

    if "overview" in skewer_data:
        out.append("* [Overview](#overview)")

    if "prerequisites" in skewer_data:
        out.append("* [Prerequisites](#prerequisites)")

    for i, step_data in enumerate(skewer_data["steps"], 1):
        title = f"Step {i}: {step_data['title']}"

        fragment = replace(title, " ", "_")
        fragment = replace(fragment, r"[\W]", "")
        fragment = replace(fragment, "_", "-")
        fragment = fragment.lower()

        out.append(f"* [{title}](#{fragment})")

    if "summary" in skewer_data:
        out.append("* [Summary](#summary)")

    if "cleaning_up" in skewer_data:
        out.append("* [Cleaning up](#cleaning-up)")

    if "next_steps" in skewer_data:
        out.append("* [Next steps](#next-steps)")

    out.append("")

    if "overview" in skewer_data:
        out.append("## Overview")
        out.append("")
        out.append(skewer_data["overview"])
        out.append("")

    if "prerequisites" in skewer_data:
        out.append("## Prerequisites")
        out.append("")
        out.append(skewer_data["prerequisites"])
        out.append("")

    for i, step_data in enumerate(skewer_data["steps"], 1):
        out.append(f"## Step {i}: {step_data['title']}")
        out.append("")
        out.append(generate_step(skewer_data, step_data))
        out.append("")

    if "summary" in skewer_data:
        out.append("## Summary")
        out.append("")
        out.append(skewer_data["summary"])
        out.append("")

    if "cleaning_up" in skewer_data:
        out.append("## Cleaning up")
        out.append("")
        out.append(generate_step(skewer_data, skewer_data["cleaning_up"]))
        out.append("")

    if "next_steps" in skewer_data:
        out.append("## Next steps")
        out.append("")
        out.append(skewer_data["next_steps"])

    write(output_file, "\n".join(out))

def generate_step(skewer_data, step_data):
    out = list()

    if "preamble" in step_data:
        out.append("")
        out.append(step_data["preamble"])

    if "commands" in step_data:
        for context_name, commands in step_data["commands"].items():
            namespace = skewer_data["contexts"][context_name]["namespace"]

            out.append("")
            out.append(f"Console for _{namespace}_:")
            out.append("")
            out.append("~~~ shell")

            for command in commands:
                out.append(command["run"])

            out.append("~~~")

    if "postamble" in step_data:
        out.append("")
        out.append(step_data["postamble"])

    return "\n".join(out)

class _StringCatalog(dict):
    def __init__(self, path):
        super(_StringCatalog, self).__init__()

        self.path = "{0}.strings".format(split_extension(path)[0])

        check_file(self.path)

        key = None
        out = list()

        for line in read_lines(self.path):
            line = line.rstrip()

            if line.startswith("[") and line.endswith("]"):
                if key:
                    self[key] = "".join(out).strip()

                out = list()
                key = line[1:-1]

                continue

            out.append(line)
            out.append("\n")

        self[key] = "".join(out).strip()

    def __repr__(self):
        return format_repr(self)

_strings = _StringCatalog(__file__)

def _string_loader(loader, node):
    return _strings[node.value]

_yaml.SafeLoader.add_constructor("!string", _string_loader)
