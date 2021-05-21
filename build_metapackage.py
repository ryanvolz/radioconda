#!/usr/bin/env python3
import pathlib
from typing import List

import yaml


def read_env_file(
    env_file: pathlib.Path,
    fallback_name: str,
    fallback_version: str,
    fallback_platform: str,
    fallback_channels: List[str],
) -> dict:
    with env_file.open("r") as f:
        env_dict = yaml.safe_load(f)

    env_dict.setdefault("name", fallback_name)
    env_dict.setdefault("version", fallback_version)
    env_dict.setdefault("platform", fallback_platform)
    env_dict.setdefault("channels", fallback_channels)

    return env_dict


def get_conda_metapackage_cmdline(
    env_dict: dict, home: str, license_id: str, summary: str
):
    cmdline = [
        "conda",
        "metapackage",
        env_dict["name"],
        env_dict["version"],
        "--no-anaconda-upload",
        "--home",
        home,
        "--license",
        license_id,
        "--summary",
        summary,
    ]
    for channel in env_dict["channels"]:
        cmdline.extend(["--channel", channel])
    cmdline.extend(["--dependencies"] + env_dict["dependencies"])

    return cmdline


if __name__ == "__main__":
    import argparse
    import os
    import subprocess
    import shutil
    import sys

    import conda_build.config

    conda_build_config = conda_build.config.Config()

    cwd = pathlib.Path(".").absolute()
    here = pathlib.Path(__file__).parent.absolute().relative_to(cwd)
    distname = os.getenv("DISTNAME", "radioconda")
    platform = os.getenv("PLATFORM", conda_build_config.subdir)
    source = "/".join(
        (
            os.getenv("GITHUB_SERVER_URL", "https://github.com"),
            os.getenv("GITHUB_REPOSITORY", "ryanvolz/radioconda"),
        )
    )
    license_id = os.getenv("LICENSE_ID", "BSD-3-Clause")
    summary = os.getenv("METAPACKAGE_SUMMARY", f"Metapackage for {distname}.")

    parser = argparse.ArgumentParser(
        description=(
            "Build environment metapackage using conda-build."
            " Additional command-line options following '--' will be passed to conda"
            " metapackage."
        )
    )
    parser.add_argument(
        "env_file",
        type=pathlib.Path,
        nargs="?",
        default=here / "installer_specs" / f"{distname}-{platform}.yml",
        help=(
            "Environment yaml file for a particular platform"
            " (name ends in the platform identifier)."
            " (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        type=pathlib.Path,
        default=here / "dist" / "conda-bld",
        help=(
            "Output directory in which the metapackage will be placed."
            " (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--home",
        default=source,
        help="The homepage for the metapackage. (default: %(default)s)",
    )
    parser.add_argument(
        "--license",
        default=license_id,
        help="The SPDX license identifier for the metapackage. (default: %(default)s)",
    )
    parser.add_argument(
        "--summary",
        default=summary,
        help="Summary of the package. (default: %(default)s)",
    )

    # allow a delimiter to separate metapackage arguments
    argv = sys.argv[1:]
    if "--" in argv:
        i = argv.index("--")
        args, metapackage_args = parser.parse_args(argv[:i]), argv[i + 1 :]
    else:
        args, metapackage_args = parser.parse_args(argv), []

    env_dict = read_env_file(
        args.env_file,
        fallback_name=distname,
        fallback_version="0",
        fallback_platform=platform,
        fallback_channels=["conda-forge"],
    )

    cmdline = get_conda_metapackage_cmdline(
        env_dict=env_dict, home=args.home, license_id=args.license, summary=args.summary
    )
    cmdline.extend(metapackage_args)

    env = os.environ.copy()
    env["CONDA_SUBDIR"] = env_dict["platform"]

    proc = subprocess.run(cmdline, env=env)

    try:
        proc.check_returncode()
    except subprocess.CalledProcessError:
        sys.exit(1)

    bldpkgs_dir = pathlib.Path(conda_build_config.croot) / env_dict["platform"]
    pkg_paths = list(bldpkgs_dir.glob(f"{env_dict['name']}-{env_dict['version']}*.bz2"))
    pkg_out_dir = args.output_dir / env_dict["platform"]
    pkg_out_dir.mkdir(parents=True, exist_ok=True)

    for pkg in pkg_paths:
        shutil.copy(pkg, pkg_out_dir)
