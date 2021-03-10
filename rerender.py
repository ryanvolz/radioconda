#!/usr/bin/env python3
import pathlib
import shutil

import conda_lock
import yaml


def render_lock_spec(
    lock_spec: conda_lock.src_parser.LockSpecification, conda_exe: str
) -> conda_lock.src_parser.LockSpecification:
    create_env_dict = conda_lock.conda_lock.solve_specs_for_arch(
        conda=conda_exe,
        channels=lock_spec.channels,
        specs=lock_spec.specs,
        platform=lock_spec.platform,
    )
    pkgs = create_env_dict["actions"]["LINK"]
    spec_names = set(
        spec.split(sep=None, maxsplit=1)[0].split(sep="=", maxsplit=1)[0]
        for spec in lock_spec.specs
    )

    rendered_specs = []
    for pkg in pkgs:
        if pkg["name"] in spec_names:
            rendered_specs.append("{name}={version}={build_string}".format(**pkg))

    rendered_lock_spec = conda_lock.src_parser.LockSpecification(
        specs=sorted(rendered_specs),
        channels=lock_spec.channels,
        platform=lock_spec.platform,
    )

    return rendered_lock_spec


def render_constructor_specs(
    environment_file: pathlib.Path,
    version: str,
    company: str,
    license_file: pathlib.Path,
    output_dir: pathlib.Path,
    conda_exe: str,
) -> dict:
    with environment_file.open("r") as f:
        env_yaml_data = yaml.safe_load(f)

    installer_name = env_yaml_data["name"]
    platforms = env_yaml_data["platforms"]

    if not license_file.exists():
        raise ValueError(f"Cannot find license file: {license_file}")

    output_dir.mkdir(parents=True, exist_ok=True)

    constructor_specs = {}

    for platform in platforms:
        constructor_name = f"{installer_name}-{platform}"

        lock_spec = conda_lock.conda_lock.parse_environment_file(
            environment_file=environment_file, platform=platform
        )
        rendered_lock_spec = render_lock_spec(lock_spec, conda_exe)
        construct_dict = dict(
            name=installer_name,
            version=version,
            company=company,
            channels=rendered_lock_spec.channels,
            specs=rendered_lock_spec.specs,
            initialize_by_default=True,
            installer_type="all",
            keep_pkgs=True,
            license_file="LICENSE",
            register_python_default=False,
            write_condarc=True,
        )
        if platform.startswith("win"):
            construct_dict["post_install"] = "post_install.bat"
        else:
            construct_dict["post_install"] = "post_install.sh"

        constructor_specs[constructor_name] = construct_dict

        constructor_dir = output_dir / constructor_name
        if constructor_dir.exists():
            shutil.rmtree(constructor_dir)
        constructor_dir.mkdir(parents=True)

        # copy license to the constructor directory
        shutil.copy(license_file, constructor_dir / "LICENSE")

        # write the post_install scripts referenced in the construct dict
        if platform.startswith("win"):
            with (constructor_dir / "post_install.bat").open("w") as f:
                f.writelines((r"del /q %PREFIX%\pkgs\*.tar.bz2", ""))
        else:
            with (constructor_dir / "post_install.sh").open("w") as f:
                f.writelines((r"rm -f $PREFIX/pkgs/*.tar.bz2", ""))

        construct_yaml_path = constructor_dir / "construct.yaml"
        with construct_yaml_path.open("w") as f:
            yaml.safe_dump(construct_dict, stream=f)

    return constructor_specs


if __name__ == "__main__":
    import argparse
    import datetime
    import os

    cwd = pathlib.Path(".").absolute()
    here = pathlib.Path(__file__).parent.absolute().relative_to(cwd)
    distname = os.getenv("DISTNAME", "radioconda")
    source = os.getenv("SOURCE", "github.com/ryanvolz/radioconda")

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
            "YAML file defining an installer distribution, with a 'name' string and"
            " 'channels', 'platforms', and 'dependencies' lists."
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

    dt = datetime.datetime.now()
    version = dt.strftime("%Y.%m.%d")

    constructor_specs = render_constructor_specs(
        environment_file=args.environment_file,
        version=version,
        company=args.company,
        license_file=args.license_file,
        output_dir=args.output_dir,
        conda_exe=conda_exe,
    )
