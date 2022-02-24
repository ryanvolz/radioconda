echo {"env_vars": {"GR_PREFIX": "", "GRC_BLOCKS_PATH": "", "UHD_PKG_PATH": "", "VOLK_PREFIX": ""}}>%PREFIX%\conda-meta\state
del /q %PREFIX%\pkgs\*.tar.bz2
exit 0
