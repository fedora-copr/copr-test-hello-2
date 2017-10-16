import logging
import os
import re
import shutil
import tarfile

from exceptions import SourceArchiveAlreadyExists

log = logging.getLogger("__main__")


def pack_sources(dir_to_pack, target_path, pack_dir_as):
    """
    Create a gzipped tar archive from the given directory.

    :param str dir_to_pack: directory to be packed
    :param str target_path: path to the resulting archive
    :param str pack_dir_as: packed directory name inside the archive
    """
    if os.path.exists(target_path):
        raise SourceArchiveAlreadyExists("{} already exists"
                                         .format(target_path))

    log.debug("Packing {} as {} into {}...".format(
        dir_to_pack, pack_dir_as, target_path))

    def exclude(tar_info):
        exclude_git_pattern = r'(/.git$|/.git/|/.gitignore$)'
        if re.search(exclude_git_pattern, tar_info.name):
            log.debug("Excluding {}".format(tar_info.name))
            return None
        return tar_info

    tarball = tarfile.open(target_path, 'w:gz')
    tarball.add(dir_to_pack, pack_dir_as, filter=exclude)
    tarball.close()


def find_source_zero(rpm_sources):
    """
    For the given list of rpm_sources,
    return filename of the Source0.

    :param list rpm_sources

    :returns str: filename of Source0 or None
    """
    for (filepath, num, flags) in rpm_sources:
        if num == 0 and flags == 1:
            return os.path.basename(filepath)
    return None
