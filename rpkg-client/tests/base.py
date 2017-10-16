import os
import unittest
import shutil
import rpm
import tempfile

from spec_templates import SPEC_TEMPLATE

class TestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def dump_spec(self, template, pkgname='testpkg', **kwargs):
        spec_content = template.substitute(kwargs, pkgname=pkgname)
        spec_path = os.path.join(
            self.tmpdir, '{}.spec'.format(pkgname))
        spec_file = open(spec_path, 'w')
        spec_file.write(spec_content)
        spec_file.close()
        return spec_path

    def touch_file(self, filename, subdir=None):
        if subdir:
            dirpath = os.path.join(self.tmpdir, subdir)
            os.makedirs(dirpath)
        else:
            dirpath = self.tmpdir
        filepath = os.path.join(dirpath, filename)
        open(filepath, 'w').close()
        return filepath

    def get_parsed_spec(self, spec_path):
        ts = rpm.ts()
        rpm.addMacro("_sourcedir", self.tmpdir)
        return ts.parseSpec(spec_path)

    def make_packed_content(self):
        spec_path = self.dump_spec(SPEC_TEMPLATE, source0='source0.tar.gz')
        self.touch_file('source0.tar.gz')

    def make_unpacked_content(self):
        spec_path = self.dump_spec(SPEC_TEMPLATE, source0='source0.tar.gz')
        self.touch_file('foobar.py')
