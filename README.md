# radioconda

![Build radioconda](https://github.com/ryanvolz/radioconda/actions/workflows/build_radioconda.yml/badge.svg)

This repository holds cross-platform installers for a collection of **software radio** packages bundled with the [conda](https://conda.io/) package manager. These installers will get you started with an environment that includes the packages listed [here](https://github.com/ryanvolz/radioconda/blob/master/radioconda.yaml). Once installed, you will have a fully functional conda distribution, meaning that you can install additional packages (if available through [conda-forge](https://conda-forge.org/feedstock-outputs)) or upgrade to the latest versions using `conda` or `mamba`, e.g.:

    mamba install <pkg-name>
    mamba upgrade --all

Think of radioconda as an alternative to [Anaconda](https://www.anaconda.com/products/individual) or [Miniforge](https://github.com/conda-forge/miniforge), but specialized for software radio.

**NOTE:** Radioconda is built from packages maintained by the [conda-forge](https://conda-forge.org/) project. If you have questions or issues that are specific to the conda installation of a particular package, please report them at the corresponding [feedstock repository](https://github.com/conda-forge/feedstocks).

## Download

Radioconda installers are available here: https://github.com/ryanvolz/radioconda/releases.

| OS      | Architecture | Installer Type | Download                                                                                                   |
| ------- | ------------ | -------------- | ---------------------------------------------------------------------------------------------------------- |
| Linux   | x86_64       | Command-line   | [radioconda-Linux-x86_64.sh](https://glare.now.sh/ryanvolz/radioconda/radioconda-.*-Linux-x86_64.sh)       |
| macOS   | x86_64       | Command-line   | [radioconda-MacOSX-x86_64.sh](https://glare.now.sh/ryanvolz/radioconda/radioconda-.*-MacOSX-x86_64.sh)     |
| macOS   | x86_64       | Graphical      | [radioconda-MacOSX-x86_64.pkg](https://glare.now.sh/ryanvolz/radioconda/radioconda-.*-MacOSX-x86_64.pkg)   |
| Windows | x86_64       | Graphical      | [radioconda-Windows-x86_64.exe](https://glare.now.sh/ryanvolz/radioconda/radioconda-.*-Windows-x86_64.exe) |

## Install

For a command line install, download the installer and run,

    bash radioconda-*-Linux-x86_64.sh   # or similar for other installers for unix platforms

For a graphical install, download the installer and double-click it.

### Non-interactive install

For non-interactive usage, look at the options by running the following:

    bash radioconda-*-Linux-x86_64.sh -h   # or similar for other installers for unix platforms

or if you are on Windows, run:

    start /wait "" build/radioconda-*-Windows-x86_64.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%UserProfile%\radioconda

## Developers

### Usage

Each installer package is built from a specification directory in [installer_specs](https://github.com/ryanvolz/radioconda/tree/master/installer_specs) using [conda constructor](https://github.com/conda/constructor). An installer can be built manually using the [build_installer.py](https://github.com/ryanvolz/radioconda/blob/master/build_installer.py) script. The specification directories set the exact versions of the included packages so that `constructor` will produce a predictable result that can be tracked by git for each release. In turn, the specification directories are created/updated by _re-rendering_ the radioconda [environment specification file](https://github.com/ryanvolz/radioconda/blob/master/radioconda.yaml) using the [rerender.py](https://github.com/ryanvolz/radioconda/blob/master/rerender.py) script.

So, the procedure to create a new installer package is:

1. Update the environment specification file `radioconda.yaml`, if desired.
2. Re-render the constructor specification directories by running `rerender.py`.
3. Commit the changes to produced by steps 1 and 2 to the git repository.
4. Build the installer package for a particular platform by running `build_installer.py`.

### Release

To release a new version of radioconda and build installer packages using GitHub's CI:

- Update the repository following steps 1-3 above.
- Make a new pre-release on GitHub with a name equal to the version.
- Wait until all artifacts are uploaded by CI
  - For each build, we upload 3 artifacts
    1. One installer with the version name
    2. One installer without the version name
    3. The SHA256
- Mark the pre-release as a release

NOTE: using a pre-release is important to make sure the latest links work.
