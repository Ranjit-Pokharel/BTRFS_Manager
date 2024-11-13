import argparse
import os
import re
import subprocess as sp
import sys


class BtrfsError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage()
        sys.exit(message)


class RunRequirement:
    def __init__(self, path):
        if os.name != "posix":
            raise BtrfsError("Invalid OS: Linux only")

        if sp.run(["which", "btrfs"], capture_output=True).returncode != 0:
            raise BtrfsError(
                "Error: btrfs tools cannot be found. See your Distribution for Installation"
            )

        if os.geteuid() != 0:
            raise BtrfsError("Invlaid privileges: must run as sudo or root user")

        if not os.path.exists(path):
            raise BtrfsError(f"invalid path: {path}")

        if (
            sp.run(["btrfs", "filesystem", "df", path], capture_output=True).returncode
            != 0
        ):
            raise BtrfsError(f"Invalid btrfs filesystem: {path}")

        check_root_mount = sp.run(
            ["findmnt", "-T", path, "-o", "SOURCE", "-n"], capture_output=True
        )
        if check_root_mount.returncode != 0:
            raise BtrfsError(f"Error: something went wrong with mount point {path}")

        btrfs_mount_path = check_root_mount.stdout.decode().strip()
        pattern = r"(\[/.*\])"
        match = re.search(pattern, btrfs_mount_path)
        if match and match.group(1):
            raise BtrfsError(
                f"Error: btrfs device root not mounted at ( {path} ) : ( {btrfs_mount_path} ) subvolume mounted"
            )


class BtrfsManager:
    def __init__(self, filesystem_path):
        self.path = filesystem_path

    # def create_snapshot(self, snapshot_name):
    #     try:
    #         command = f"btrfs subvolume snapshot {self.filesystem_path} {snapshot_name}"
    #         sp.run(command, check=True, shell=True)
    #         return f"Snapshot '{snapshot_name}' created successfully"
    #     except sp.CalledProcessError:
    #         return f"Error: Snapshot '{snapshot_name}' creation failed"

    def list_subvolumes(self):
        command = ["btrfs", "subvolume", "list", self.path]

        result = sp.run(command, capture_output=True)
        message = result.stdout.decode().strip()
        if result.returncode != 0:
            raise BtrfsError(f"Error: {message}")
        return message


def main():
    arg = parser()

    path = arg.file_path

    try:
        RunRequirement(path)
    except BtrfsError as e:
        sys.exit(e)

    btrfs = BtrfsManager(path)

    if arg.list:
        try:
            print(btrfs.list_subvolumes())
        except BaseException as e:
            sys.exit(e)


def parser():
    parse = ArgumentParser(description="Process some command-line arguments.")
    parse.add_argument(
        "-f",
        "--file_path",
        type=str,
        help="Path to the file",
        required=True,
        metavar="</path/to/btrfs>",
    )
    parse.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List subvolumes in the Btrfs filesystem",
    )

    return parse.parse_args()


main()
