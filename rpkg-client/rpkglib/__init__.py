import os
import rpm
import shutil
import re

import pyrpkg
from pyrpkg.utils import cached_property
from pyrpkg.errors import rpkgError
from pyrpkg.sources import SourcesFile

from rpkglib.lookaside import CGILookasideCache
from rpkglib import utils

from exceptions import NotUnpackedException, RpmSpecParseException, NoSourceZeroException

class Commands(pyrpkg.Commands):
    def __init__(self, *args, **kwargs):
        """Init the object and some configuration details."""
        super(Commands, self).__init__(*args, **kwargs)
        self.source_entry_type = 'bsd'
        self.distgit_namespaced = True
        self.lookaside_namespaced = True
        self._ns_module_name = None

    def load_rpmdefines(self):
        """Populate rpmdefines"""
        self._rpmdefines = [
            "--define '_sourcedir %s'" % self.path,
            "--define '_specdir %s'" % self.path,
            "--define '_builddir %s'" % self.path,
            "--define '_srcrpmdir %s'" % self.path,
            "--define '_rpmdir %s'" % self.path,
        ]

    @cached_property
    def lookasidecache(self):
        return CGILookasideCache(
            self.lookasidehash, self.lookaside, self.lookaside_cgi,
            client_cert=self.cert_file, ca_cert=self.ca_cert)

    @property
    def ns_module_name(self):
        if not self._ns_module_name:
            self.load_ns_module_name()
        return self._ns_module_name

    def load_ns_module_name(self):
        """Loads the namespace module name"""
        try:
            replacements = {'user': self.user, 'module':'(.*)/?'}
            gitbaseurl_pattern = self.gitbaseurl%replacements + '$'
            anongiturl_pattern = self.anongiturl%replacements + '$'

            match = re.match(gitbaseurl_pattern, self.push_url)
            if not match:
                match = re.match(anongiturl_pattern, self.push_url)

            if match:
                ns_module_name = match.group(1)
                if ns_module_name.endswith('.git'):
                    ns_module_name = ns_module_name[:-len('.git')]
                self._ns_module_name = ns_module_name
                return
        except rpkgError:
            pass

        self._ns_module_name = self.module_name

    def sources(self, outdir=None):
        """Download source files"""
        if not os.path.exists(self.sources_filename):
            return

        # Default to putting the files where the module is
        if not outdir:
            outdir = self.path

        sourcesf = SourcesFile(self.sources_filename, self.source_entry_type)

        for entry in sourcesf.entries:
            outfile = os.path.join(outdir, entry.file)
            self.lookasidecache.download(
                self.ns_module_name,
                entry.file, entry.hash, outfile,
                hashtype=entry.hashtype)

    def srpm(self, outdir=None):
        """Create an srpm using hashtype from content in the module

        Requires sources already downloaded.
        """

        self.srpmname = os.path.join(self.path, "%s-%s-%s.src.rpm"
                                     % (self.module_name, self.ver, self.rel))

        # See if we need to build the srpm
        if os.path.exists(self.srpmname):
            self.log.debug('Srpm found, rewriting it.')

        cmd = ['rpmbuild']
        cmd.extend(self.rpmdefines)
        if self.quiet:
            cmd.append('--quiet')
        # This may need to get updated if we ever change our checksum default
        if not self.hashtype == 'sha256':
            cmd.extend(["--define '_source_filedigest_algorithm %s'"
                        % self.hashtype,
                        "--define '_binary_filedigest_algorithm %s'"
                        % self.hashtype])
        if outdir:
            cmd.extend(["--define '_srcrpmdir %s'" % outdir])

        cmd.extend(['--nodeps', '-bs', os.path.join(self.path, self.spec)])
        self._run_command(cmd, shell=True)

    def is_unpacked(self, dirpath, rpm_sources):
        """
        Decide, whether we are dealing with "unpacked"
        or "packed" type of source content at the
        given dirpath.

        "packed": does not contain anything else
                  except ignored files or contains
                  at least one source referenced
                  by the given specfile

        "unpacked": is not "packed", meaning that
                    it contains at least one non-ignored
                    file and contains no file referenced
                    by the given specfile as a source

        "source" in these definitions is a filename
        specified in a Source or Patch .spec directive

        NOTE:

        This criterion needs source list parsed from
        a specfile to make the decision, which makes
        it potentially dependant on the given environment
        where it is executed. You can try to avoid this
        dependency e.g. by not using Patch and Source
        spec directives inside conditionals and not
        using environment-dependant rpmmacros in Patch
        and Source definitions.

        :param str dirpath: filesystem path to a directory
                with the source content
        :param list rpm_sources: list of tuples describing
                rpm sources

        :returns True if the directory content is of the
                unpacked type, False otherwise
        """
        for (filepath, num, flags) in rpm_sources:
            filename = os.path.basename(filepath)

            local_filepath = os.path.join(dirpath, filename)
            if os.path.isfile(local_filepath):
                return False

        ignore_file_regex = '(^README|.spec$|^\.|^tito.props$|^sources$)'
        ignored_file_filter = lambda f: not re.search(
            ignore_file_regex, f, re.IGNORECASE)

        if not list(filter(ignored_file_filter, os.listdir(dirpath))):
            return False

        return True

    def make_source(self, destdir=None):
        """
        Create source mentioned according to Source0 spec
        directive from an unpacked repository. Does nothing
        on a packed repo.

        NOTE:

        This method calls rpm's parseSpec, evaluation
        of which is heavily dependant on the environment
        (e.g. currently defined macros under /usr/lib/rpm
        and ~/.rpmmacros), where it is being executed.

        Therefore, it should be called in a clean environment
        of the target rpm distribution and architecture.

        Note that if you invoke this method directly on your
        host system, you need to trust the provided spec file.
        When specfile is parsed, %() constructs get evaluated
        and any system command can be executed from there.
        The behaviour is the same as if you called rpmbuild
        directly in your system.

        :param str destdir: where to put the generated sources

        :returns path to the packed archive (alias Source0)
        """
        spec_path = os.path.join(self.path, self.spec)

        ts = rpm.ts()
        try:
            rpm.addMacro("_sourcedir", self.path)
            rpm_spec = ts.parseSpec(spec_path)
        except ValueError as e:
            raise RpmSpecParseException(str(e))

        if not self.is_unpacked(self.path, rpm_spec.sources):
            raise NotUnpackedException("Not an unpacked content.")

        source_zero_name = utils.find_source_zero(rpm_spec.sources)
        if not source_zero_name:
            raise NoSourceZeroException("Source zero not found")

        target_source_path = os.path.join(
            destdir or self.path, source_zero_name)

        name = rpm.expandMacro("%{name}")
        version = rpm.expandMacro("%{version}")
        rpm.reloadConfig()

        packed_dir_name = name + '-' + version
        utils.pack_sources(
            self.path,
            target_source_path,
            packed_dir_name
        )
        self.log.info('Wrote: {}'.format(target_source_path))
        return target_source_path
