"""
Created on May 28, 2011

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.

This module emits the version.py file contents which are used in the
build process to indicate the time that this version was built.

"""

import sys

from arelle._pkg_meta import version


IS_64_BIT_PYTHON = sys.maxsize == 0x7fffffffffffffff
if len(sys.argv) > 1 and sys.argv[1]:
    # Add name suffix, like ER3 or TKTABLE.
    VERSION_STRING = "-".join([version, sys.argv[1]])
else:
    VERSION_STRING = version


def write_version_text():
    """
    Creates a version.txt file based off the VERSION_STRING constant.
    """
    with open("version.txt", "w") as fh:
        fh.write(VERSION_STRING)


def mac_script():
    """
    Builds the shell script to rename the distribution for MacOS.
    """
    with open("buildRenameDmg.sh", "w") as script:
        script.write(
            "mv dist_dmg/arelle.dmg dist_dmg/arelle-macOS-{}.dmg\n"
            .format(VERSION_STRING)
        )


def linux2_script():
    """
    Builds the shell script to rename the distribution for "linux2" systems.
    """
    with open("buildRenameLinux-x86_64.sh", "w") as script:
        script.write(
            "mv dist/exe.linux-x86_64-{}.{}.tar.gz "
            "dist/arelle-linux-x86_64-{}.tar.gz\n"
            .format(
                sys.version_info[0], sys.version_info[1],
                VERSION_STRING
            )
        )


def linux_script():
    """
    Builds the shell script to rename the distribution for linux.
    """
    if len(sys.argv) > 1 and sys.argv[1]:
        sysName = sys.argv[1]
    else:
        sysName = "linux"
    with open("buildRenameLinux-x86_64.sh", "w") as script:
        script.write(
            "mv dist/exe.linux-x86_64-{}.{}.tar.gz "
            "dist/arelle-{}-x86_64-{}.tar.gz\n"
            .format(
                sys.version_info[0], sys.version_info[1],
                sysName, VERSION_STRING
            )
        )


def spark_script():
    """
    Builds the spark shell script to rename the distribution for Spark.
    """
    with open("buildRenameSol10Sun4.sh", "w") as script:
        script.write(
            "mv dist/exe.solaris-2.10-sun4v{0}-{1}.{2}.tar.gz "
            "dist/arelle-solaris10-sun4{0}-{3}.tar.gz\n"
            .format(
                ".64bit" if IS_64_BIT_PYTHON else "",
                sys.version_info[0], sys.version_info[1],
                VERSION_STRING
            )
        )


def windows_script():
    """
    Builds the various Windows batch files for renaming distributions.
    """
    with open("buildRenameX86.bat", "w") as script:
        script.write(
            "rename dist\\arelle-win-x86.exe arelle-win-x86-{}.exe\n"
            .format(VERSION_STRING)
        )
    with open("buildRenameX64.bat", "w") as script:
        script.write(
            "rename dist\\arelle-win-x64.exe arelle-win-x64-{}.exe\n"
            .format(VERSION_STRING)
        )
    with open("buildRenameSvr27.bat", "w") as script:
        script.write(
            "rename dist\\arelle-svr-2.7.zip arelle-svr-2.7-{}.zip\n"
            .format(VERSION_STRING)
        )
    with open("buildRenameZip32.bat", "w") as script:
        script.write(
            "rename dist\\arelle-cmd32.zip arelle-cmd32-{}.zip\n"
            .format(VERSION_STRING)
        )
    with open("buildRenameZip64.bat", "w") as script:
        script.write(
            "rename dist\\arelle-cmd64.zip arelle-cmd64-{}.zip\n"
            .format(VERSION_STRING)
        )


def unknown_script():
    """
    No-op function to handle unknown system types.
    """
    pass


SCRIPT_SWITCH = {
    "darwin": mac_script,
    "linux2": linux2_script,
    "linux": linux_script,
    "sunos5": spark_script,
    "win": windows_script
}

if __name__ == "__main__":
    write_version_text()
    if sys.platform.startswith("win"):
        script_builder = SCRIPT_SWITCH.get("win")
    else:
        script_builder = SCRIPT_SWITCH.get(sys.platform, unknown_script)
    script_builder()
