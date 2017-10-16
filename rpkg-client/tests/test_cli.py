import unittest
import rpkglib
import six
import base
import os
import glob
import tempfile

from six.moves import configparser
from rpkglib.cli import rpkgClient
from rpkglib.exceptions import NotUnpackedException

from spec_templates import SPEC_TEMPLATE

if six.PY3:
    from unittest import mock
    from unittest.mock import MagicMock
else:
    import mock
    from mock import MagicMock

RPKG_CONFIG = """
[rpkg]
lookaside = http://localhost/repo/pkgs
lookaside_cgi = https://localhost/repo/pkgs/upload.cgi
gitbaseurl = ssh://%(user)s@localhost/%(module)s
anongiturl = git://localhost/%(module)s
"""

class TestCli(base.TestCase):
    def setUp(self):
        super(TestCli, self).setUp()
        config_fd, self.config_path = tempfile.mkstemp()
        config_file = os.fdopen(config_fd, 'w+')
        config_file.write(RPKG_CONFIG)
        config_file.close()

        config = configparser.SafeConfigParser()
        config.read(self.config_path)

        self.client = rpkgClient(config, name='rpkg')
        self.client.do_imports('rpkglib')
        self.client.args = MagicMock(user='user', q='q', path=self.tmpdir)

    def tearDown(self):
        os.unlink(self.config_path)
        super(TestCli, self).tearDown()

    @mock.patch('rpkglib.Commands')
    def test_load_cmd(self, cmds):
        self.client.load_cmd()
        cmds.assert_called_with(
            self.tmpdir,
            'http://localhost/repo/pkgs',
            'sha512',
            'https://localhost/repo/pkgs/upload.cgi',
            'ssh://%(user)s@localhost/%(module)s',
            'git://localhost/%(module)s',
            branchre='.*',
            kojiconfig='',
            build_client=None,
            user='user',
            quiet='q',
            realms=[],
        )

    def test_make_source_from_packed_raises(self):
        self.make_packed_content()
        self.client.args.spec = ''
        with self.assertRaises(NotUnpackedException):
            self.client.make_source()

    def test_make_source_from_unpacked(self):
        self.make_unpacked_content()
        self.client.args.outdir = self.tmpdir
        self.client.args.spec = ''
        self.client.make_source()
        self.assertTrue(glob.glob('{}/{}'.format(self.tmpdir, '*.tar.gz')))

    def test_unpacked_changes_into_packed_by_make_sources(self):
        self.make_unpacked_content()
        self.client.args.outdir = self.tmpdir
        self.client.args.spec = ''
        self.client.make_source()
        self.assertTrue(glob.glob('{}/{}'.format(self.tmpdir, '*.tar.gz')))
        with self.assertRaises(NotUnpackedException):
            self.client.make_source()

    def test_make_srpm_from_packed(self):
        self.make_packed_content()
        dircontent = os.listdir(self.tmpdir)
        self.client.args.spec = ''
        self.client.args.outdir = self.tmpdir
        self.client.srpm()
        self.assertItemsEqual(
            os.listdir(self.tmpdir),
            dircontent+['testpkg-1-1.src.rpm'])

    def test_make_srpm_from_unpacked(self):
        self.make_unpacked_content()
        dircontent = os.listdir(self.tmpdir)
        self.client.args.spec = ''
        self.client.args.outdir = self.tmpdir
        self.client.srpm()
        self.assertItemsEqual(
            os.listdir(self.tmpdir),
            dircontent+['testpkg-1-1.src.rpm', 'source0.tar.gz'])

    def test_make_srpm_multiple_specs(self):
        spec1_path = self.dump_spec(
            SPEC_TEMPLATE, pkgname='testpkg1', source0='source0.tar.gz')
        spec2_path = self.dump_spec(
            SPEC_TEMPLATE, pkgname='testpkg2', source0='source0.tar.gz')
        self.touch_file('source0.tar.gz')
        dircontent = os.listdir(self.tmpdir)

        self.client.args.outdir = self.tmpdir

        self.client.args.spec = spec1_path
        self.client.srpm()
        self.assertItemsEqual(
            os.listdir(self.tmpdir),
            dircontent+['testpkg1-1-1.src.rpm'])

        os.unlink(os.path.join(self.tmpdir, 'testpkg1-1-1.src.rpm'))

        self.client.args.spec = spec2_path
        self.client.srpm()
        self.assertItemsEqual(
            os.listdir(self.tmpdir),
            dircontent+['testpkg2-1-1.src.rpm'])
