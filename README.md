# radioconda

![Build radioconda](https://github.com/ryanvolz/radioconda/actions/workflows/build_radioconda.yml/badge.svg)

This repository holds cross-platform installers for a collection of open source **software radio** packages bundled with the [conda](https://conda.io/) package manager, including

- Digital RF
- GNU Radio
- gqrx
- gr-satellites

and support for the following SDR devices and device libraries:

|      Device      |             Library              |
| :--------------: | :------------------------------: |
| [ADALM-PLUTO][1] | libiio ([setup](#iio-pluto-sdr)) |
| [Ettus USRPs][2] |  UHD ([setup](#uhd-ettus-usrp))  |
|   [LimeSDR][3]   |  Lime Suite ([setup](#limesdr))  |
|   [RTL-SDR][4]   |   rtl-sdr ([setup](#rtl-sdr))    |

[1]: https://www.analog.com/en/design-center/evaluation-hardware-and-software/evaluation-boards-kits/adalm-pluto.html
[2]: https://www.ettus.com/products/
[3]: https://limemicro.com/products/boards/
[4]: https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/

The complete list of packages can be found [here](https://github.com/ryanvolz/radioconda/blob/master/radioconda.yaml).

Once installed, you will have a fully functional conda distribution/environment, meaning that you can use the `conda` or `mamba` commands to install additional packages (if available through [conda-forge](https://conda-forge.org/feedstock-outputs)) or upgrade to the latest versions. Think of radioconda as an alternative to [Anaconda](https://www.anaconda.com/products/individual) or [Miniforge](https://github.com/conda-forge/miniforge), but specialized for software radio.

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

For a command line install, download the installer and run:

    bash radioconda-*-Linux-x86_64.sh   # or similar for other installers for unix platforms

For a graphical install, download the installer and double-click it.

See [below](#additional-installation-for-device-support) for additional installation steps for particular software radio devices.

### Non-interactive install

For non-interactive usage, look at the options by running the following:

    bash radioconda-*-Linux-x86_64.sh -h   # or similar for other installers for unix platforms

or if you are on Windows, run:

    start /wait "" build/radioconda-<VERSION>-Windows-x86_64.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%UserProfile%\radioconda

## Use

You will mostly use radioconda through the command line, although on Windows some applications will install shortcuts to the Start menu.

### Windows

Launch a terminal by running "Conda Prompt" in the "radioconda" directory in the Start menu. From this command line, you can run `mamba` to install/upgrade packages or run any of the applications installed with radioconda. Some applications can also be launched through shortcuts added to the Start menu.

### Linux and macOS

Launch your favorite terminal. Depending on the options you chose while installing, you may or may not already have the radioconda "base" environment activated automatically (you will see "(base)" on your command line prompt). To otherwise activate the radioconda "base" environment, run:

    conda activate base

If this fails because the `conda` command is not found, you can activate the environment manually by running

    sh <PATH_TO_RADIOCONDA>/bin/activate

From an activated environment, you will be able to run `mamba` to install/upgrade packages or run any of the applications installed with radioconda.

### Installing packages

To install a particular package:

    mamba install <pkg-name>

## Upgrade

Once you have radioconda installed, you can stay up to date for all packages with:

    mamba upgrade --all

### Upgrade to latest release

To install the latest release in particular, run (on Windows):

    mamba install --file https://github.com/ryanvolz/radioconda/releases/latest/download/radioconda-win-64.txt

(on Linux/macOS):

    mamba install --file https://github.com/ryanvolz/radioconda/releases/latest/download/radioconda-$(conda info | sed -n -e 's/^.*platform : //p').txt

### Install a particular release

To install the package versions associated with a particular release, substitute the release number and run the following (on Windows):

    mamba install --file https://github.com/ryanvolz/radioconda/releases/download/20NN.NN.NN/radioconda-win-64.txt

(on Linux/macOS):

    mamba install --file https://github.com/ryanvolz/radioconda/releases/download/20NN.NN.NN/radioconda-$(conda info | sed -n -e 's/^.*platform : //p').txt

## Additional Installation for Device Support

To use particular software radio devices, it might be necessary to install additional drivers or firmware. Find your device below and follow the instructions. (Help add to this section by filing an issue if the instructions don't work or you have additional instructions to add!)

### RTL-SDR

#### Windows users

[Install the WinUSB driver with Zadig](#installing-the-winusb-driver-with-zadig), selecting the device that is called "Bulk-In, Interface (Interface 0)".

#### Linux users

Blacklist the DVB-T modules that would otherwise claim the device:

    sudo ln -s $CONDA_PREFIX/etc/modprobe.d/rtl-sdr-blacklist.conf /etc/modprobe.d/radioconda-rtl-sdr-blacklist.conf
    sudo modprobe -r $(cat $CONDA_PREFIX/etc/modprobe.d/rtl-sdr-blacklist.conf | sed -n -e 's/^blacklist //p')

Install a udev rule by creating a link into your radioconda installation:

    sudo ln -s $CONDA_PREFIX/lib/udev/rules.d/rtl-sdr.rules /etc/udev/rules.d/radioconda-rtl-sdr.rules
    sudo udevadm control --reload
    sudo udevadm trigger

### IIO (Pluto SDR)

#### Windows users

Install the latest USB drivers by download and installing [this file](https://github.com/analogdevicesinc/plutosdr-m2k-drivers-win/releases/latest/download/PlutoSDR-M2k-USB-Drivers.exe).

#### Linux users

Install a udev rule by creating a link into your radioconda installation:

    sudo ln -s $CONDA_PREFIX/lib/udev/rules.d/90-libiio.rules /etc/udev/rules.d/90-radioconda-libiio.rules
    sudo udevadm control --reload
    sudo udevadm trigger

#### All users

Once you can talk to the hardware (by following the instructions below), you may want to perform the post-install steps detailed on the [Pluto users wiki](https://wiki.analog.com/university/tools/pluto/users).

### LimeSDR

#### Windows users

The conda-forge package uses libusb to communicate over USB with your LimeSDR device, instead of the standard CyUSB library which is not open source. If you have used your LimeSDR with another software package, you will have to switch USB drivers to one compatible with WinUSB/libusb.

[Install the WinUSB driver with Zadig](#installing-the-winusb-driver-with-zadig), selecting your Lime device.

#### Linux users

Install a udev rule by creating a link into your radioconda installation:

    sudo ln -s $CONDA_PREFIX/lib/udev/rules.d/64-limesuite.rules /etc/udev/rules.d/64-radioconda-limesuite.rules
    sudo udevadm control --reload
    sudo udevadm trigger

### UHD (Ettus USRP)

#### All devices

Download the firmware files by activating your conda prompt and running

    uhd_images_downloader

#### USB devices (e.g. B series)

Windows users might have to install a USB driver for the device. Follow the instructions [from the Ettus site](https://files.ettus.com/manual/page_transport.html#transport_usb_installwin), or [install the WinUSB driver with Zadig](#installing-the-winusb-driver-with-zadig) (your device will have a USB ID that starts with 2500).

## Installing the WinUSB driver with Zadig

Many USB devices use libusb and need a WinUSB driver installed on Windows. Follow this procedure to install the driver for your device:

1. Download and run [Zadig](https://zadig.akeo.ie/)
2. Select your device

   - It may be auto-selected since it is missing a driver
   - It may not have a sensible name, but you can verify the USB ID

3. Ensure the target driver (middle of the interface) reads "WinUSB"
4. Click "Install Driver" or "Replace Driver"

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

1. Update the repository following steps 1-3 above.
2. Make a new pre-release on GitHub with a name equal to the version.
3. Wait until all artifacts are uploaded by CI
4. Mark the pre-release as a release

NOTE: using a pre-release is important to make sure the "latest" links work.
