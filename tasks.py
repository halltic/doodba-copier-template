"""Template maintenance tasks.

These tasks are to be executed with https://www.pyinvoke.org/ in Python 3.8.1+
and are related to the maintenance of this template project, not the child
projects generated with it.
"""
import re
from pathlib import Path
from unittest import mock

from invoke import task
from invoke.util import yaml

TEMPLATE_ROOT = Path(__file__).parent.resolve()
ESSENTIALS = ("git", "python3", "poetry")


def _load_copier_conf():
    """Load copier.yml."""
    with open("copier.yml") as copier_fd:
        # HACK https://stackoverflow.com/a/44875714/1468388
        # TODO Remove hack when https://github.com/pyinvoke/invoke/issues/708 is fixed
        with mock.patch.object(
            yaml.reader.Reader,
            "NON_PRINTABLE",
            re.compile(
                "[^\x09\x0A\x0D\x20-\x7E\x85\xA0-"
                "\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]"
            ),
        ):
            return yaml.safe_load(copier_fd)


@task
def check_dependencies(c):
    """Check essential development dependencies are present."""
    failures = []
    for dependency in ESSENTIALS:
        try:
            c.run(f"{dependency} --version", hide=True)
        except Exception:
            failures.append(dependency)
    if failures:
        print(f"Missing essential dependencies: {failures}")


@task(check_dependencies)
def develop(c):
    """Set up a development environment."""
    with c.cd(str(TEMPLATE_ROOT)):
        c.run("git submodule update --init --checkout --recursive")
        # Use poetry to set up development environment in a local venv
        c.run("poetry install")
        c.run("poetry run pre-commit install")


@task(develop)
def lint(c, verbose=False):
    """Lint & format source code."""
    flags = ["--show-diff-on-failure", "--all-files", "--color=always"]
    if verbose:
        flags.append("--verbose")
    flags = " ".join(flags)
    with c.cd(str(TEMPLATE_ROOT)):
        c.run(f"poetry run pre-commit run {flags}")


@task(develop)
def test(c, verbose=False, sequential=False, docker=True):
    """Test project.

    Add --sequential to run only sequential tests, with parallelization disabled.
    """
    flags = ["--color=yes"]
    if verbose:
        flags.append("-vv")
    if not docker:
        flags.append("--skip-docker-tests")
    if sequential:
        flags.extend(["-m", "sequential"])
    else:
        flags.extend(["-n", "auto", "-m", '"not sequential"'])
    flags = " ".join(flags)
    cmd = f"poetry run pytest {flags} tests"
    with c.cd(str(TEMPLATE_ROOT)):
        c.run(cmd)

@task(
    help={
        "length": "Length of the password to generate. Default: 64",
    },
)
def generate_password(c, length=64):
    """Generate secure passwords and create environment files.

    Generates secure passwords for ADMIN_PASSWORD and POSTGRES_PASSWORD,
    and creates the necessary .env files in the .docker directory.
    """
    def _generate_password(length=64):
        """Generate a secure password with mixed character types."""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(length))
            # Ensure at least one character from each category
            if (
                any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in string.punctuation for c in password)
            ):
                return password

    output_dir = PROJECT_ROOT / ".docker"
    output_dir.mkdir(exist_ok=True)

    admin_password = _generate_password(length)
    postgres_password = _generate_password(length)

    # Create odoo.env
    with open(output_dir / "odoo.env", "w") as f:
        f.write(f"ADMIN_PASSWORD={admin_password}\n")

    # Create db-creation.env
    with open(output_dir / "db-creation.env", "w") as f:
        f.write(f"POSTGRES_PASSWORD={postgres_password}\n")

    # Create db-access.env
    with open(output_dir / "db-access.env", "w") as f:
        f.write(f"PGPASSWORD={postgres_password}\n")

    _logger.info("Passwords and env files generated in .docker/")
    _logger.info(f"Generated passwords with length: {length}")
