#!/usr/bin/env python3
import contextlib
import math
import pathlib
import shutil
from typing import Any, Dict, Optional

import conda_lock
import diff_match_patch
import yaml
from conda_package_streaming.package_streaming import stream_conda_component
from conda_package_streaming.url import conda_reader_for_url
from PIL import Image


def resize_contain(image, size, resample=Image.LANCZOS, bg_color=(255, 255, 255, 0)):
    """
    Resize image according to size.
    image:      a Pillow image instance
    size:       a list of two integers [width, height]
    """
    img_format = image.format
    img = image.copy()
    img.thumbnail((size[0], size[1]), resample)
    background = Image.new("RGBA", (size[0], size[1]), bg_color)
    img_position = (
        int(math.ceil((size[0] - img.size[0]) / 2)),
        int(math.ceil((size[1] - img.size[1]) / 2)),
    )
    background.paste(img, img_position)
    background.format = img_format
    return background.convert("RGBA")


def name_from_pkg_spec(spec: str):
    return (
        spec.split(sep=None, maxsplit=1)[0]
        .split(sep="=", maxsplit=1)[0]
        .split(sep="::", maxsplit=1)[-1]
    )


def write_env_file(
    env_dict: Dict[str, Any],
    file_path: pathlib.Path,
    name: Optional[str] = None,
    version: Optional[str] = None,
    platform: Optional[str] = None,
    variables: Optional[dict] = None,
):
    if name:
        env_dict["name"] = name
    if version:
        env_dict["version"] = version
    if platform:
        env_dict["platform"] = platform
    if variables:
        env_dict["variables"] = variables
    with file_path.open("w") as f:
        yaml.safe_dump(env_dict, stream=f)

    return env_dict


def render_metapackage_environments(
    lockfile_path: pathlib.Path,
    requested_pkg_names: Dict[str, Any],
    name: str,
    version: str,
    output_dir: pathlib.Path,
) -> None:
    lock_content = conda_lock.conda_lock.parse_conda_lock_file(lockfile_path)
    lock_work_dir = lockfile_path.parent

    # render main env spec into environment file for creating metapackage
    conda_lock.conda_lock.do_render(
        lockfile=lock_content,
        kinds=("env",),
        filename_template=f"{lock_work_dir}/{name}-{{platform}}.metapackage",
    )
    # process and save rendered platform env files to the output directory
    for platform_env_yaml_path in lock_work_dir.glob("*.metapackage.yml"):
        platform_env_yaml_name = platform_env_yaml_path.name.partition(".")[0]
        platform = platform_env_yaml_name.split(sep="-", maxsplit=1)[1]

        with platform_env_yaml_path.open("r") as f:
            platform_env_dict = yaml.safe_load(f)

        dependencies = sorted(platform_env_dict["dependencies"])
        # filter the dependency list by the explicitly listed package names
        platform_env_dict["dependencies"] = [
            spec
            for spec in dependencies
            if name_from_pkg_spec(spec) in requested_pkg_names
        ]

        if platform.startswith("win"):
            variables = dict(
                GR_PREFIX="", GRC_BLOCKS_PATH="", UHD_PKG_PATH="", VOLK_PREFIX=""
            )
        else:
            variables = None
        write_env_file(
            env_dict=platform_env_dict,
            file_path=output_dir / f"{platform_env_yaml_name}.yml",
            name=name,
            version=version,
            platform=platform,
            variables=variables,
        )


def render_constructors(
    lockfile_path: pathlib.Path,
    requested_pkg_names: Dict[str, Any],
    name: str,
    version: str,
    company: str,
    license_file: pathlib.Path,
    output_dir: pathlib.Path,
    builder_lockfile_path: pathlib.Path,
    logo_path: Optional[pathlib.Path] = None,
) -> None:
    lock_content = conda_lock.conda_lock.parse_conda_lock_file(lockfile_path)
    lock_work_dir = lockfile_path.parent

    builder_lock_content = conda_lock.conda_lock.parse_conda_lock_file(
        builder_lockfile_path
    )
    constructor_lockdeps = [
        lockdep
        for lockdep in builder_lock_content.package
        if lockdep.name == "constructor"
    ]

    # render main + installer env specs into environment file for creating installer
    conda_lock.conda_lock.do_render(
        lockfile=lock_content,
        kinds=("env",),
        filename_template=f"{lock_work_dir}/{name}-{{platform}}.constructor",
        extras=("installer",),
    )

    if logo_path is not None:
        logo = Image.open(logo_path)

    for platform_env_yaml_path in lock_work_dir.glob("*.constructor.yml"):
        constructor_name = platform_env_yaml_path.name.partition(".")[0]
        platform = constructor_name.split(sep="-", maxsplit=1)[1]

        constructor_dir = output_dir / constructor_name
        if constructor_dir.exists():
            shutil.rmtree(constructor_dir)
        constructor_dir.mkdir(parents=True)

        with platform_env_yaml_path.open("r") as f:
            platform_env_dict = yaml.safe_load(f)

        # filter requested_pkg_names by locked environment to account for selectors
        platform_env_pkg_names = [
            name_from_pkg_spec(spec) for spec in platform_env_dict["dependencies"]
        ]
        user_requested_specs = [
            name for name in requested_pkg_names if name in platform_env_pkg_names
        ]

        construct_dict = dict(
            name=name,
            version=version,
            company=company,
            channels=platform_env_dict["channels"],
            specs=sorted(platform_env_dict["dependencies"]),
            user_requested_specs=user_requested_specs,
            initialize_by_default=False if platform.startswith("win") else True,
            installer_type="all",
            keep_pkgs=True,
            license_file="LICENSE",
            register_python_default=False,
            write_condarc=True,
            condarc=dict(
                channels=platform_env_dict["channels"],
                channel_priority="strict",
            ),
        )
        if logo_path is not None:
            if platform.startswith("win"):
                # convert to RGB (no transparency) and set white background
                # because constructor eventually converts to bmp without transparency
                welcome_image = resize_contain(
                    logo.convert("RGB"), (164, 314), bg_color=(255, 255, 255, 255)
                )
                header_image = resize_contain(
                    logo.convert("RGB"), (150, 57), bg_color=(255, 255, 255, 255)
                )
                icon_image = resize_contain(logo, (256, 256))

                welcome_image.save(constructor_dir / "welcome.png")
                header_image.save(constructor_dir / "header.png")
                icon_image.save(constructor_dir / "icon.png")

                construct_dict["welcome_image"] = "welcome.png"
                construct_dict["header_image"] = "header.png"
                construct_dict["icon_image"] = "icon.png"
            elif platform.startswith("osx"):
                welcome_image = resize_contain(logo, (1227, 600))
                welcome_image.save(constructor_dir / "welcome.png")
                construct_dict["welcome_image"] = "welcome.png"
        if platform.startswith("win"):
            construct_dict["post_install"] = "post_install.bat"
            # point to template that we generate at build time with a patch over default
            construct_dict["nsis_template"] = "main.nsi.tmpl"
        else:
            construct_dict["post_install"] = "post_install.sh"

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
                            r"del /q %PREFIX%\pkgs\*.conda",
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
                            r"rm -f $PREFIX/pkgs/*.tar.bz2 $PREFIX/pkgs/*.conda",
                            "exit 0",
                            "",
                        )
                    )
                )

        construct_yaml_path = constructor_dir / "construct.yaml"
        with construct_yaml_path.open("w") as f:
            yaml.safe_dump(construct_dict, stream=f)

        if platform.startswith("win"):
            # patch constructor's nsis template
            constructor_platform_lockdeps = [
                lockdep
                for lockdep in constructor_lockdeps
                if lockdep.platform == platform
            ]
            if constructor_platform_lockdeps:
                lockdep = constructor_platform_lockdeps[0]

                # get the NSIS template that comes with the locked constructor package
                constructor_filename, constructor_pkg = conda_reader_for_url(
                    lockdep.url
                )
                with contextlib.closing(constructor_pkg):
                    for tar, member in stream_conda_component(
                        constructor_filename, constructor_pkg, component="pkg"
                    ):
                        if (
                            member.name
                            == "site-packages/constructor/nsis/main.nsi.tmpl"
                        ):
                            locked_nsi_tmpl = tar.extractfile(member).read().decode()
                            break
                # read the original and custom NSIS templates
                local_constructor_nsis = pathlib.Path("constructor") / "nsis"
                with (local_constructor_nsis / "main.nsi.tmpl.orig").open("r") as f:
                    orig_nsi_tmpl = f.read()
                with (local_constructor_nsis / "main.nsi.tmpl").open("r") as f:
                    custom_nsi_tmpl = f.read()

                # get patch from original NSIS template to locked version we will be
                # building with and apply it to the custom template
                dmp = diff_match_patch.diff_match_patch()
                line_orig, line_locked, line_array = dmp.diff_linesToChars(
                    orig_nsi_tmpl, locked_nsi_tmpl
                )
                diffs = dmp.diff_main(line_orig, line_locked, checklines=False)
                dmp.diff_charsToLines(diffs, line_array)
                patches = dmp.patch_make(orig_nsi_tmpl, diffs)
                patched_nsi_tmpl, results = dmp.patch_apply(patches, custom_nsi_tmpl)
                if not all(results):
                    raise RuntimeError("Conflicts found when patching NSIS template")

                # write patched template to constructor dir
                with (constructor_dir / "main.nsi.tmpl").open("w") as f:
                    f.write(patched_nsi_tmpl)

                # update orig and custom with locked and patched
                with (local_constructor_nsis / "main.nsi.tmpl.orig").open("w") as f:
                    f.write(locked_nsi_tmpl)
                with (local_constructor_nsis / "main.nsi.tmpl").open("w") as f:
                    f.write(patched_nsi_tmpl)


def render(
    environment_file: pathlib.Path,
    installer_environment_file: pathlib.Path,
    builder_environment_file: pathlib.Path,
    version: str,
    company: str,
    license_file: pathlib.Path,
    output_dir: pathlib.Path,
    conda_exe: pathlib.Path,
    logo_path: Optional[pathlib.Path] = None,
    dirty: Optional[bool] = False,
    keep_workdir: Optional[bool] = False,
) -> None:
    with environment_file.open("r") as f:
        env_yaml_data = yaml.safe_load(f)
    with installer_environment_file.open("r") as f:
        base_env_yaml_data = yaml.safe_load(f)

    env_name = env_yaml_data["name"]
    env_pkg_names = [name_from_pkg_spec(spec) for spec in env_yaml_data["dependencies"]]
    base_env_pkg_names = [
        name_from_pkg_spec(spec) for spec in base_env_yaml_data["dependencies"]
    ]

    if not license_file.exists():
        raise ValueError(f"Cannot find license file: {license_file}")

    if output_dir.exists() and not dirty:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # working dir for conda-lock outputs that we use as intermediates
    lock_work_dir = output_dir / "lockwork"
    lock_work_dir.mkdir(parents=True, exist_ok=True)

    # create the locked build environment specification
    builder_lockfile_path = output_dir / "buildenv.conda-lock.yml"
    conda_lock.conda_lock.run_lock(
        environment_files=[builder_environment_file],
        conda_exe=conda_exe,
        mamba=True,
        micromamba=True,
        kinds=("lock",),
        lockfile_path=builder_lockfile_path,
    )

    # read environment files and create the lock file
    lockfile_path = lock_work_dir / f"{env_name}.conda-lock.yml"
    conda_lock.conda_lock.run_lock(
        environment_files=[environment_file, installer_environment_file],
        conda_exe=conda_exe,
        mamba=True,
        micromamba=True,
        kinds=("lock",),
        lockfile_path=lockfile_path,
    )

    # render main environment specs into explicit .lock files for reproducibility
    lock_content = conda_lock.conda_lock.parse_conda_lock_file(lockfile_path)
    conda_lock.conda_lock.do_render(
        lockfile=lock_content,
        kinds=("explicit",),
        filename_template=f"{output_dir}/{env_name}-{{platform}}.lock",
    )

    # create the environment specification files for the metapackages
    render_metapackage_environments(
        lockfile_path=lockfile_path,
        requested_pkg_names=env_pkg_names,
        name=env_name,
        version=version,
        output_dir=output_dir,
    )

    # create the rendered constructor directories
    render_constructors(
        lockfile_path=lockfile_path,
        requested_pkg_names=sorted(env_pkg_names + base_env_pkg_names),
        name=env_name,
        version=version,
        company=company,
        license_file=license_file,
        output_dir=output_dir,
        builder_lockfile_path=builder_lockfile_path,
        logo_path=logo_path,
    )

    # clean up conda-lock work dir
    if not keep_workdir:
        shutil.rmtree(lock_work_dir)


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
        "builder_environment_file",
        type=pathlib.Path,
        nargs="?",
        default=here / "buildenv.yaml",
        help=(
            "YAML file defining the builder environment for running conda-constructor,"
            " with a 'name' string and 'channels', 'platforms', and 'dependencies'"
            " lists."
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
        "--logo",
        dest="logo_path",
        type=pathlib.Path,
        default=here / "static" / f"{distname}_logo.png",
        help=(
            "File containing the logo image to include in the installer."
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
        "--dirty",
        action="store_true",
        default=False,
        help=("Do not clean up output_dir before rendering. (default: %(default)s)"),
    )
    parser.add_argument(
        "--keep-workdir",
        action="store_true",
        default=False,
        help=(
            "Keep conda-lock working directory ({output_dir}/lockwork) of intermediate"
            " outputs. (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--conda-exe",
        type=pathlib.Path,
        default=None,
        help=(
            "Path to the conda (or mamba or micromamba) executable to use."
            " (default: search for conda/mamba/micromamba)"
        ),
    )

    args = parser.parse_args()

    render(
        environment_file=args.environment_file,
        installer_environment_file=args.installer_environment_file,
        builder_environment_file=args.builder_environment_file,
        version=args.version,
        company=args.company,
        license_file=args.license_file,
        output_dir=args.output_dir,
        conda_exe=args.conda_exe,
        logo_path=args.logo_path,
        dirty=args.dirty,
        keep_workdir=args.keep_workdir,
    )
