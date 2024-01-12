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

@command(passthrough=True)
def test(verbose=False, quiet=False, passthrough_args=[]):
    clean()

    if verbose:
        passthrough_args.append("--verbose")

    if quiet:
        passthrough_args.append("--quiet")

    args = " ".join(passthrough_args)

    import skewer.tests
    PlanoTestCommand(skewer.tests).main(passthrough_args)

@command
def coverage():
    """
    Run the tests and measure code coverage
    """

    check_program("coverage")

    with working_env(PYTHONPATH="python"):
        run("coverage run --source skewer -m skewer.tests")

    run("coverage report")
    run("coverage html")

    print(f"file:{get_current_dir()}/htmlcov/index.html")

@command
def render():
    """
    Render README.html from README.md
    """
    check_program("pandoc")

    run(f"pandoc -o README.html README.md")

    print(f"file:{get_real_path('README.html')}")

@command
def clean():
    remove(join("python", "__pycache__"))
    remove(join("test-example", "python", "__pycache__"))
    remove("README.html")
    remove("htmlcov")
    remove(".coverage")

@command
def update_plano():
    """
    Update the embedded Plano repo
    """
    make_dir("external")
    remove("external/plano-main")
    run("curl -sfL https://github.com/ssorj/plano/archive/main.tar.gz | tar -C external -xz", shell=True)
