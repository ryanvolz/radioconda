#!/usr/bin/env python3
import pathlib
import re

comment_re = re.compile(r"^\s*#\s*(?P<comment>.*)\s*$")
key_value_re = re.compile(r"^(?P<key>.*):\s*(?P<value>.*)\s*$")


def read_lock_file(lock_file: pathlib.Path) -> dict:
    with lock_file.open("r") as f:
        lines = f.read().splitlines()

    lock_dict = dict(specs=[])
    for line in lines:
        comment_match = comment_re.match(line)
        if comment_match:
            m = key_value_re.match(comment_match.group("comment"))
            if m:
                lock_dict[m.group("key")] = m.group("value")
        else:
            lock_dict["specs"].append(line)

    return lock_dict


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
            " Additional command-line options will be passed to conda metapackage."
        )
    )
    parser.add_argument(
        "lock_file",
        type=pathlib.Path,
        nargs="?",
        default=here / "installer_specs" / f"{distname}-{platform}.txt",
        help=(
            "Environment lock file for a particular platform"
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

    args, metapackage_args = parser.parse_known_args()

    lock_dict = read_lock_file(args.lock_file)

    name = lock_dict.get("name", distname)
    version = lock_dict.get("version", "0")
    platform = lock_dict.get("platform", platform)

    env = os.environ.copy()
    env["CONDA_SUBDIR"] = platform

    channels = [c.strip() for c in lock_dict.get("channels", "conda-forge").split(",")]

    conda_metapackage_cmdline = [
        "conda",
        "metapackage",
        name,
        version,
        "--no-anaconda-upload",
        "--home",
        args.home,
        "--license",
        args.license,
        "--summary",
        args.summary,
    ]
    for channel in channels:
        conda_metapackage_cmdline.extend(["--channel", channel])
    conda_metapackage_cmdline.extend(["--dependencies"] + lock_dict["specs"])
    conda_metapackage_cmdline.extend(metapackage_args)

    proc = subprocess.run(conda_metapackage_cmdline, env=env)

    try:
        proc.check_returncode()
    except subprocess.CalledProcessError:
        sys.exit(1)

    bldpkgs_dir = pathlib.Path(conda_build_config.bldpkgs_dir)
    pkg_paths = list(bldpkgs_dir.glob(f"{name}-{version}*.bz2"))
    pkg_out_dir = args.output_dir / platform
    pkg_out_dir.mkdir(parents=True, exist_ok=True)

    for pkg in pkg_paths:
        shutil.copy(pkg, pkg_out_dir)
