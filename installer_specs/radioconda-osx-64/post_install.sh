#!/bin/sh
PREFIX="${PREFIX:-$2/radioconda}"
rm -f $PREFIX/pkgs/*.tar.bz2 $PREFIX/pkgs/*.conda
exit 0
