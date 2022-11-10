#!/usr/bin/env python3
import pathlib
import shutil
from typing import List, Optional

import conda_lock
import yaml


def name_from_pkg_spec(spec: str):
    return spec.split(sep=None, maxsplit=1)[0].split(sep="=", maxsplit=1)[0]


def lock_env_spec(
    lock_spec: conda_lock.src_parser.LockSpecification, conda_exe: str
) -> conda_lock.src_parser.LockSpecification:
    create_env_dict = conda_lock.conda_lock.solve_specs_for_arch(
        conda=conda_exe,
        channels=lock_spec.channels,
        specs=lock_spec.specs,
        platform=lock_spec.platform,
    )
    pkgs = create_env_dict["actions"]["LINK"]
    locked_specs = ["{name}={version}={build_string}".format(**pkg) for pkg in pkgs]

    locked_env_spec = conda_lock.src_parser.LockSpecification(
        specs=sorted(locked_specs),
        channels=lock_spec.channels,
        platform=lock_spec.platform,
        virtual_package_repo=conda_lock.virtual_package.default_virtual_package_repodata(),
    )

    return locked_env_spec


def write_env_file(
    env_spec: conda_lock.src_parser.LockSpecification,
    file_path: pathlib.Path,
    name: Optional[str] = None,
    version: Optional[str] = None,
    variables: Optional[dict] = None,
):
    env_dict = dict(
        name=name,
        version=version,
        platform=env_spec.platform,
        channels=env_spec.channels,
        dependencies=env_spec.specs,
    )
    if name:
        env_dict["name"] = name
    if version:
        env_dict["version"] = version
    if variables:
        env_dict["variables"] = variables
    with file_path.open("w") as f:
        yaml.safe_dump(env_dict, stream=f)

    return env_dict


def write_lock_file(
    lock_spec: conda_lock.src_parser.LockSpecification,
    file_path: pathlib.Path,
    conda_exe: str,
):
    lockfile_contents = conda_lock.conda_lock.create_lockfile_from_spec(
        conda=conda_exe, spec=lock_spec, kind="explicit"
    )

    def sanitize_lockfile_line(line):
        line = line.strip()
        if line == "":
            return "#"
        else:
            return line

    lockfile_contents = [sanitize_lockfile_line(ln) for ln in lockfile_contents]

    with file_path.open("w") as f:
        f.write("\n".join(lockfile_contents) + "\n")

    return lockfile_contents


def render_constructor(
    lock_spec: conda_lock.src_parser.LockSpecification,
    name: str,
    version: str,
    company: str,
    license_file: pathlib.Path,
    output_dir: pathlib.Path,
) -> dict:
    platform = lock_spec.platform
    constructor_name = f"{name}-{platform}"

    construct_dict = dict(
        name=name,
        version=version,
        company=company,
        condarc=dict(
            channels=lock_spec.channels,
            channel_priority="strict",
        ),
        channels=lock_spec.channels,
        specs=lock_spec.specs,
        initialize_by_default=False if platform.startswith("win") else True,
        installer_type="all",
        keep_pkgs=True,
        license_file="LICENSE",
        register_python_default=False,
        write_condarc=True,
    )
    if platform.startswith("win"):
        construct_dict["post_install"] = "post_install.bat"
        # point to template that we generate at build time with a patch over default
        construct_dict["nsis_template"] = "main.nsi.tmpl"
    else:
        construct_dict["post_install"] = "post_install.sh"

    constructor_dir = output_dir / constructor_name
    if constructor_dir.exists():
        shutil.rmtree(constructor_dir)
    constructor_dir.mkdir(parents=True)

    # copy license to the constructor directory
    shutil.copy(license_file, constructor_dir / "LICENSE")

    # write the post_install scripts referenced in the construct dict
    if platform.startswith("win"):
        with (constructor_dir / "post_install.bat").open("w") as f:
            f.write(
                "\n".join(
                    (
                        r'echo {"env_vars": {"GR_PREFIX": "", "GRC_BLOCKS_PATH": "", "UHD_PKG_PATH": "", "VOLK_PREFIX": ""}}>%PREFIX%\conda-meta\state',
                        r"del /q %PREFIX%\pkgs\*.tar.bz2",
                        "exit 0",
                        "",
                    )
                )
            )
    else:
        with (constructor_dir / "post_install.sh").open("w") as f:
            f.write(
                "\n".join(
                    (
                        "#!/bin/sh",
                        f'PREFIX="${{PREFIX:-$2/{name}}}"',
                        r"rm -f $PREFIX/pkgs/*.tar.bz2",
                        "exit 0",
                        "",
                    )
                )
            )

    construct_yaml_path = constructor_dir / "construct.yaml"
    with construct_yaml_path.open("w") as f:
        yaml.safe_dump(construct_dict, stream=f)

    return construct_dict


def render_platforms(
    environment_file: pathlib.Path,
    installer_environment_file: pathlib.Path,
    version: str,
    company: str,
    license_file: pathlib.Path,
    output_dir: pathlib.Path,
    conda_exe: str,
) -> dict:
    with environment_file.open("r") as f:
        env_yaml_data = yaml.safe_load(f)

    env_name = env_yaml_data["name"]
    platforms = env_yaml_data["platforms"]

    if not license_file.exists():
        raise ValueError(f"Cannot find license file: {license_file}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    rendered_platforms = {}

    for platform in platforms:
        output_name = f"{env_name}-{platform}"

        # get the environment specification for the list of packages from the env file
        env_spec = conda_lock.conda_lock.parse_environment_file(
            environment_file=environment_file, platform=platform
        )
        env_pkg_names = [name_from_pkg_spec(spec) for spec in env_spec.specs]

        # lock the full environment specification to specific versions and builds
        locked_env_spec = lock_env_spec(env_spec, conda_exe)

        if platform.startswith("win"):
            variables = dict(
                GR_PREFIX="", GRC_BLOCKS_PATH="", UHD_PKG_PATH="", VOLK_PREFIX=""
            )
        else:
            variables = None

        # write the full environment specification to a lock file (to install from file)
        lockfile_contents = write_lock_file(
            lock_spec=locked_env_spec,
            file_path=output_dir / f"{output_name}.lock",
            conda_exe=conda_exe,
        )

        # filter the full package spec by the explicitly listed package names
        metapackage_pkg_specs = [
            spec
            for spec in locked_env_spec.specs
            if name_from_pkg_spec(spec) in env_pkg_names
        ]
        metapackage_spec = conda_lock.src_parser.LockSpecification(
            specs=metapackage_pkg_specs,
            channels=locked_env_spec.channels,
            platform=locked_env_spec.platform,
        )

        # write the filtered environment spec to a yaml file (to build metapackage)
        locked_env_dict = write_env_file(
            env_spec=metapackage_spec,
            file_path=output_dir / f"{output_name}.yml",
            name=env_name,
            version=version,
            variables=variables,
        )

        # add installer-only (base environment) packages and lock those too
        installer_pkg_spec = conda_lock.conda_lock.parse_environment_file(
            environment_file=installer_environment_file, platform=platform
        )
        installer_spec = conda_lock.src_parser.LockSpecification(
            specs=sorted(locked_env_spec.specs + installer_pkg_spec.specs),
            channels=sorted(
                set(locked_env_spec.channels) | set(installer_pkg_spec.channels)
            ),
            platform=locked_env_spec.platform,
        )
        locked_installer_spec = lock_env_spec(installer_spec, conda_exe)

        # get a set of only the packages to put in the constructor specification
        # taken from the installer-only list and those explicitly selected originally
        constructor_pkg_names = set(
            name_from_pkg_spec(spec)
            for spec in env_spec.specs + installer_pkg_spec.specs
        )

        # filter the installer spec by the constructor package names
        constructor_pkg_specs = [
            spec
            for spec in locked_installer_spec.specs
            if name_from_pkg_spec(spec) in constructor_pkg_names
        ]
        constructor_spec = conda_lock.src_parser.LockSpecification(
            specs=constructor_pkg_specs,
            channels=locked_installer_spec.channels,
            platform=locked_installer_spec.platform,
        )

        # create the rendered constructor directory
        constructor_dict = render_constructor(
            lock_spec=constructor_spec,
            name=env_name,
            version=version,
            company=company,
            license_file=license_file,
            output_dir=output_dir,
        )

        # aggregate output
        rendered_platforms[output_name] = dict(
            locked_env_spec=locked_env_spec,
            locked_env_dict=locked_env_dict,
            lockfile_contents=lockfile_contents,
            locked_installer_spec=locked_installer_spec,
            constructor_dict=constructor_dict,
        )

    return rendered_platforms


if __name__ == "__main__":
    import argparse
    import datetime
    import os

    cwd = pathlib.Path(".").absolute()
    here = pathlib.Path(__file__).parent.absolute().relative_to(cwd)
    distname = os.getenv("DISTNAME", "radioconda")
    source = "/".join(
        (
            os.getenv("GITHUB_SERVER_URL", "https://github.com"),
            os.getenv("GITHUB_REPOSITORY", "ryanvolz/radioconda"),
        )
    )

    dt = datetime.datetime.now()
    version = dt.strftime("%Y.%m.%d")

    parser = argparse.ArgumentParser(
        description=(
            "Re-render installer specification directories to be used by conda"
            " constructor."
        )
    )
    parser.add_argument(
        "environment_file",
        type=pathlib.Path,
        nargs="?",
        default=here / f"{distname}.yaml",
        help=(
            "YAML file defining a distribution, with a 'name' string and"
            " 'channels', 'platforms', and 'dependencies' lists."
            " (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "installer_environment_file",
        type=pathlib.Path,
        nargs="?",
        default=here / f"{distname}_installer.yaml",
        help=(
            "YAML file defining additional packages for the installer, with a 'name'"
            " string and 'channels' and 'dependencies' lists."
            " (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        default=version,
        help=(
            "Version tag for the installer, defaults to the current date."
            " (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--company",
        type=str,
        default=source,
        help=(
            "Name of the company/entity who is responsible for the installer."
            " (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "-l",
        "--license_file",
        type=pathlib.Path,
        default=here / "LICENSE",
        help=(
            "File containing the license that applies to the installer."
            " (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        type=pathlib.Path,
        default=here / "installer_specs",
        help=(
            "Output directory in which the installer specifications will be rendered."
            " (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--conda-exe",
        type=str,
        default=None,
        help=(
            "Path to the conda (or mamba or micromamba) executable to use."
            " (default: search for conda/mamba/micromamba)"
        ),
    )

    args = parser.parse_args()

    conda_exe = conda_lock.conda_lock.determine_conda_executable(
        conda_executable=args.conda_exe, mamba=True, micromamba=True
    )

    constructor_specs = render_platforms(
        environment_file=args.environment_file,
        installer_environment_file=args.installer_environment_file,
        version=args.version,
        company=args.company,
        license_file=args.license_file,
        output_dir=args.output_dir,
        conda_exe=conda_exe,
    )
