import unittest
import os
import tarfile
import six
import git

import base
import rpkglib
from rpkglib.exceptions import NotUnpackedException, RpmSpecParseException,\
        NoSourceZeroException
from rpkglib.utils import find_source_zero
from spec_templates import SPEC_TEMPLATE, SPEC_WITH_PATCH_TEMPLATE,\
        INVALID_SPEC_TEMPLATE, NO_SOURCE_ZERO_SPEC_TEMPLATE

if six.PY3:
    from unittest import mock
    from unittest.mock import MagicMock
else:
    import mock
    from mock import MagicMock

class TestCommands(base.TestCase):
    def setUp(self):
        super(TestCommands, self).setUp()
        self.cmd = rpkglib.Commands(self.tmpdir,
                                    'lookaside',
                                    'lookasidehash',
                                    'lookaside_cgi',
                                    'ssh://someuser@copr-dist-git.fedorainfracloud.org/%(module)s',
                                    'http://copr-dist-git.fedorainfracloud.org/git/%(module)s',
                                    branchre='.*',
                                    kojiconfig='',
                                    build_client=None)

    def tearDown(self):
        super(TestCommands, self).tearDown()

    def test_load_ns_module_name_on_basegiturl(self):
        repo = git.Repo.init(self.tmpdir)
        repo.create_remote('origin', 'ssh://someuser@copr-dist-git.fedorainfracloud.org/a/b/c.git')
        self.cmd.load_ns_module_name()
        self.assertEquals(self.cmd.ns_module_name, 'a/b/c')

    def test_load_ns_module_name_on_anongiturl(self):
        repo = git.Repo.init(self.tmpdir)
        repo.create_remote('origin', 'http://copr-dist-git.fedorainfracloud.org/git/a/b/c')
        self.cmd.load_ns_module_name()
        self.assertEquals(self.cmd.ns_module_name, 'a/b/c')

    @mock.patch("rpkglib.SourcesFile")
    def test_sources_empty_sources(self, sources_file):
        self.touch_file('sources')
        self.cmd.lookasidecache.download = MagicMock()
        self.cmd.sources()
        sources_file.assert_called_with('{}/{}'.format(self.tmpdir, 'sources'), 'bsd')
        self.cmd.lookasidecache.download.assert_not_called()

    def test_sources_new_format(self):
        sources_path = os.path.join(self.tmpdir, 'sources')
        sources = open(sources_path, 'w')
        sources.write('SHA512 (copr-rpmbuild-0.6.tar.gz) = '
                      '7f6239543c2104443b6409fc3033f939f77e64e297399ef9831e77156ac42f6545b680fa35e99a575ca812e5ba0f17c999bfba6d0b783471fa4515182c4ba313')
        sources.close()

        # create repo for ns_module_name determining
        repo = git.Repo.init(self.tmpdir)
        repo.create_remote('origin', 'http://copr-dist-git.fedorainfracloud.org/git/testpkg')

        self.cmd.lookasidecache.download = MagicMock()
        self.cmd.sources()
        self.cmd.lookasidecache.download.assert_called_once_with(
            'testpkg',
            'copr-rpmbuild-0.6.tar.gz',
            '7f6239543c2104443b6409fc3033f939f77e64e297399ef9831e77156ac42f6545b680fa35e99a575ca812e5ba0f17c999bfba6d0b783471fa4515182c4ba313',
            '{}/{}'.format(self.tmpdir, 'copr-rpmbuild-0.6.tar.gz'),
            hashtype='sha512')

    def test_sources_old_format(self):
        sources_path = os.path.join(self.tmpdir, 'sources')
        sources = open(sources_path, 'w')
        sources.write('70e17e21942515952b4050b370fc2141  tendrl-gluster-integration-1.5.2.tar.gz')
        sources.close()

        # create repo for ns_module_name determining
        repo = git.Repo.init(self.tmpdir)
        repo.create_remote('origin', 'http://copr-dist-git.fedorainfracloud.org/git/ns/testpkg')

        self.cmd.lookasidecache.download = MagicMock()
        self.cmd.sources()
        self.cmd.lookasidecache.download.assert_called_once_with(
            'ns/testpkg',
            'tendrl-gluster-integration-1.5.2.tar.gz',
            '70e17e21942515952b4050b370fc2141',
            '{}/{}'.format(self.tmpdir, 'tendrl-gluster-integration-1.5.2.tar.gz'),
            hashtype='md5')

    def test_srpm(self):
        spec_path = self.dump_spec(SPEC_TEMPLATE, source0='source0.tar.gz')
        self.touch_file('source0.tar.gz')
        self.cmd._run_command = MagicMock()
        self.cmd.srpm()
        cmd_templated = ['rpmbuild', "--define '_sourcedir {path}'", "--define '_specdir {path}'",
                         "--define '_builddir {path}'", "--define '_srcrpmdir {path}'",
                         "--define '_rpmdir {path}'", '--nodeps', '-bs', '{path}/testpkg.spec']
        cmd = [part.format(path=self.tmpdir) for part in cmd_templated]
        self.cmd._run_command.assert_called_with(cmd, shell=True)

    def test_is_unpacked_source_is_present(self):
        spec_path = self.dump_spec(SPEC_TEMPLATE, source0='source0.tar.gz')
        self.touch_file('source0.tar.gz')
        parsed_spec = self.get_parsed_spec(spec_path)
        is_unpacked = self.cmd.is_unpacked(self.tmpdir, parsed_spec.sources)
        self.assertFalse(is_unpacked)

    def test_is_unpacked_source_not_present(self):
        spec_path = self.dump_spec(SPEC_TEMPLATE, source0='source0.tar.gz')
        self.touch_file('source1.tar.gz')
        parsed_spec = self.get_parsed_spec(spec_path)
        is_unpacked = self.cmd.is_unpacked(self.tmpdir, parsed_spec.sources)
        self.assertTrue(is_unpacked)

    def test_is_unpacked_patch_present(self):
        spec_path = self.dump_spec(
            SPEC_WITH_PATCH_TEMPLATE, source0='source0.tar.gz', patch0='patch.txt')
        self.touch_file('patch.txt')
        parsed_spec = self.get_parsed_spec(spec_path)
        is_unpacked = self.cmd.is_unpacked(self.tmpdir, parsed_spec.sources)
        self.assertFalse(is_unpacked)

    def test_is_unpacked_ignored_files(self):
        spec_path = self.dump_spec(SPEC_TEMPLATE, source0='source0.tar.gz')
        parsed_spec = self.get_parsed_spec(spec_path)
        is_unpacked = self.cmd.is_unpacked(self.tmpdir, parsed_spec.sources)
        self.assertFalse(is_unpacked)

        ignored_filenames = [
            'README', 'readme', 'README.md',
            'tito.props', 'x.spec', 'sources', '.hiddden'
        ]

        for filename in ignored_filenames:
            self.touch_file(filename)

        is_unpacked = self.cmd.is_unpacked(self.tmpdir, parsed_spec.sources)
        self.assertFalse(is_unpacked)

        self.touch_file('non-ignored-filename')
        is_unpacked = self.cmd.is_unpacked(self.tmpdir, parsed_spec.sources)
        self.assertTrue(is_unpacked)

        self.touch_file('source0.tar.gz')
        is_unpacked = self.cmd.is_unpacked(self.tmpdir, parsed_spec.sources)
        self.assertFalse(is_unpacked)

    def test_make_source_raises_on_packed(self):
        self.dump_spec(SPEC_TEMPLATE, source0='source0.tar.gz')
        with self.assertRaises(NotUnpackedException):
            self.cmd.make_source(self.tmpdir)

    def test_make_source_packs_on_unpacked(self):
        spec_path = self.dump_spec(SPEC_TEMPLATE, source0='source0.tar.gz')
        self.touch_file('patch.txt', subdir='dir')
        archive_path = self.cmd.make_source(self.tmpdir)
        self.assertTrue(os.path.exists(archive_path))

        parsed_spec = self.get_parsed_spec(spec_path)
        source0_filename = find_source_zero(parsed_spec.sources)
        self.assertEquals(os.path.basename(archive_path), source0_filename)

        parsed_spec = self.get_parsed_spec(spec_path)
        source0_filename = find_source_zero(parsed_spec.sources)
        self.assertEquals(os.path.basename(archive_path), source0_filename)

        expected_names = sorted([
            'testpkg-1', 'testpkg-1/dir', 'testpkg-1/dir/patch.txt', 'testpkg-1/testpkg.spec'
        ])
        tarball = tarfile.open(archive_path, 'r:gz')
        self.assertEquals(expected_names, sorted(tarball.getnames()))

    def test_make_source_raises_on_invalid_spec(self):
        self.dump_spec(INVALID_SPEC_TEMPLATE)
        with self.assertRaises(RpmSpecParseException):
            self.cmd.make_source(self.tmpdir)

    def test_make_source_raises_on_no_source_zero(self):
        self.dump_spec(NO_SOURCE_ZERO_SPEC_TEMPLATE)
        self.touch_file('patch.txt')
        with self.assertRaises(NoSourceZeroException):
            self.cmd.make_source(self.tmpdir)
