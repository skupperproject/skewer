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

from skewer import *

@test
def check_environment_():
    check_environment()

@test
def generate_readme_():
    with working_dir("test-example"):
        generate_readme("skewer.yaml", "README.md")
        check_file("README.md")

@test
def await_resource_():
    try:
        run("minikube -p skewer start")

        with expect_error():
            await_resource("deployment", "not-there", timeout=1)

        with expect_error():
            await_external_ip("service", "not-there", timeout=1)
    finally:
        run("minikube -p skewer delete")

@test
def run_steps_minikube_():
    with working_dir("test-example"):
        with working_env(SKEWER_DEMO=1, SKEWER_DEMO_NO_WAIT=1):
            run_steps_minikube("skewer.yaml", debug=True)

@test
def run_steps_external_():
    check_program("minikube")

    try:
        run("minikube -p skewer start")

        east_kubeconfig = make_temp_file()
        west_kubeconfig = make_temp_file()

        for kubeconfig in (east_kubeconfig, west_kubeconfig):
            with working_env(KUBECONFIG=kubeconfig):
                run("minikube -p skewer update-context")
                check_file(ENV["KUBECONFIG"])

        with open("/tmp/minikube-tunnel-output", "w") as tunnel_output_file:
            with start("minikube -p skewer tunnel", output=tunnel_output_file):
                with working_dir("test-example"):
                    run_steps_external("skewer.yaml", east=east_kubeconfig, west=west_kubeconfig, debug=True)
    finally:
        run("minikube -p skewer delete")

if __name__ == "__main__":
    from plano.commands import PlanoTestCommand
    from . import tests

    PlanoTestCommand(tests).main()
