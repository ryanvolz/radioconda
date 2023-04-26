#!/usr/bin/env python3
import pathlib
import re
import tarfile

import requests

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


def get_micromamba(cache_dir, platform, version=None) -> pathlib.Path:
    if not version:
        version = "latest"
    tarfile_path = cache_dir / f"micromamba-{platform}-{version}.bz2"
    tarfile_path.parent.mkdir(parents=True, exist_ok=True)
    micromamba_url = f"https://micro.mamba.pm/api/micromamba/{platform}/{version}"

    if not tarfile_path.exists():
        print("Downloading micromamba for bundling into installer...")
        response = requests.get(url=micromamba_url, stream=True)

        with open(tarfile_path, "wb") as micromamba_tarfile:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    micromamba_tarfile.write(chunk)
        print("...download finished!")

    extract_path = tarfile_path.parent / tarfile_path.stem
    if platform.startswith("win"):
        micromamba_path = extract_path / "Library" / "bin" / "micromamba.exe"
    else:
        micromamba_path = extract_path / "bin" / "micromamba"
    if not micromamba_path.exists():
        tarfile_obj = tarfile.open(tarfile_path, mode="r")
        tarfile_obj.extractall(extract_path)

    return micromamba_path


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
            " Additional command-line options following '--' will be passed to"
            " constructor."
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
    parser.add_argument(
        "--micromamba_version",
        default="1.3.1",
        help=(
            "Version of micromamba to download and bundle into the installer."
            " (default: %(default)s)"
        ),
    )

    # allow a delimiter to separate constructor arguments
    argv = sys.argv[1:]
    if "--" in argv:
        i = argv.index("--")
        args, constructor_args = parser.parse_args(argv[:i]), argv[i + 1 :]
    else:
        args, constructor_args = parser.parse_args(argv), []

    platform = spec_dir_extract_platform(args.installer_spec_dir)

    if platform.startswith("win"):
        # patch constructor's nsis template
        import patch_ng

        pset = patch_ng.fromfile(
            "static/0001-Customize-Windows-NSIS-installer-script.patch"
        )
        pset.write_hunks(
            pathlib.Path(constructor_main.__file__).parent / "nsis" / "main.nsi.tmpl",
            args.installer_spec_dir / "main.nsi.tmpl",
            pset.items[0].hunks,
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if not platform.startswith("win"):
        conda_exe_path = get_micromamba(
            cache_dir=args.output_dir / "tmp",
            platform=platform,
            version=args.micromamba_version,
        )
        if not conda_exe_path.exists():
            raise RuntimeError(
                f"Failed to download/extract micromamba to {conda_exe_path}"
            )
        conda_exe_args = ["--conda-exe", conda_exe_path]
    else:
        conda_exe_args = []

    constructor_cmdline = (
        [
            "constructor",
            args.installer_spec_dir,
            "--platform",
            platform,
            "--output-dir",
            args.output_dir,
        ]
        + conda_exe_args
        + constructor_args
    )

    print(" ".join(map(str, constructor_cmdline)))
    proc = subprocess.run(constructor_cmdline)

    try:
        proc.check_returncode()
    except subprocess.CalledProcessError:
        sys.exit(1)
