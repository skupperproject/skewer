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
def run_on_minikube():
    with working_dir("test-example"):
        run_steps_on_minikube("skewer.yaml", debug=True)

if __name__ == "__main__":
    import skewer.tests
    run_tests(skewer.tests)
