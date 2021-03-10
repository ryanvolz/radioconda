#!/usr/bin/env python3
import pathlib
import re

platform_re = re.compile("^.*-(?P<platform>[(?:linux)(?:osx)(?:win)].*)$")


def spec_dir_extract_platform(installer_spec_dir: pathlib.Path) -> str:
    spec_dir_name = installer_spec_dir.name

    platform_match = platform_re.match(spec_dir_name)

    if platform_match:
        return platform_match.group("platform")
    else:
        raise ValueError(
            f"Could not identify platform from directory name: {spec_dir_name}"
        )


if __name__ == "__main__":
    import argparse
    import os
    import subprocess
    import sys

    from constructor import main as constructor_main

    cwd = pathlib.Path(".").absolute()
    here = pathlib.Path(__file__).parent.absolute().relative_to(cwd)
    distname = os.getenv("DISTNAME", "radioconda")
    platform = os.getenv("PLATFORM", constructor_main.cc_platform)

    parser = argparse.ArgumentParser(
        description=(
            "Build installer package(s) using conda constructor."
            " Additional command-line options will be passed to constructor."
        )
    )
    parser.add_argument(
        "installer_spec_dir",
        type=pathlib.Path,
        nargs="?",
        default=here / "installer_specs" / f"{distname}-{platform}",
        help=(
            "Installer specification directory (containing construct.yaml)"
            " for a particular platform (name ends in the platform identifier)."
            " (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        type=pathlib.Path,
        default=here / "dist",
        help=(
            "Output directory in which the installer package(s) will be placed."
            " (default: %(default)s)"
        ),
    )

    args, constructor_args = parser.parse_known_args()

    platform = spec_dir_extract_platform(args.installer_spec_dir)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    constructor_cmdline = [
        "constructor",
        args.installer_spec_dir,
        "--platform",
        platform,
        "--output-dir",
        args.output_dir,
    ] + constructor_args

    proc = subprocess.run(constructor_cmdline)

    try:
        proc.check_returncode()
    except subprocess.CalledProcessError:
        sys.exit(1)
