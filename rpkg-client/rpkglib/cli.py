import argparse
import os
import rpm

from pyrpkg.cli import cliClient
from pyrpkg import utils

from exceptions import NotUnpackedException, RpmSpecParseException

class rpkgClient(cliClient):
    def __init__(self, config, name=None):
        self.DEFAULT_CLI_NAME = 'rpkg'
        super(rpkgClient, self).__init__(config, name)

    def setup_argparser(self):
        """Setup the argument parser and register some basic commands."""

        self.parser = argparse.ArgumentParser(
            prog=self.name,
            epilog='For detailed help pass --help to a target')

        # Add some basic arguments that should be used by all.
        # Add a config file
        self.parser.add_argument('--config', '-C',
                                 default=None,
                                 help='Specify a config file to use')
        # Allow forcing the package name
        self.parser.add_argument('--module-name',
                                 help='Override the module name. Otherwise'
                                      ' it is discovered from: Git push URL'
                                      ' or Git URL. ')
        # Override the  discovered user name
        self.parser.add_argument('--user', default=None,
                                 help='Override the discovered user name')
        # Let the user define a path to work in rather than cwd
        self.parser.add_argument('--path', default=None,
                                 type=utils.u,
                                 help='Define the directory to work in '
                                 '(defaults to cwd)')
        # Verbosity
        self.parser.add_argument('--verbose', '-v', dest='v',
                                 action='store_true',
                                 help='Run with verbose debug output')
        self.parser.add_argument('--debug', '-d', dest='debug',
                                 action='store_true',
                                 help='Run with debug output')
        self.parser.add_argument('-q', action='store_true',
                                 help='Run quietly only displaying errors')

    def setup_subparsers(self):
        """Setup basic subparsers that all clients should use"""

        # Setup some basic shared subparsers

        # help command
        self.register_help()

        # Add a common parsers
        self.register_rpm_common()

        # Other targets
        self.register_make_source()
        self.register_clean()
        self.register_clog()
        self.register_clone()
        self.register_copr_build()
        self.register_commit()
        self.register_compile()
        self.register_diff()
        self.register_gimmespec()
        self.register_giturl()
        self.register_import_srpm()
        self.register_install()
        self.register_is_packed()
        self.register_lint()
        self.register_local()
        self.register_new()
        self.register_new_sources()
        self.register_patch()
        self.register_prep()
        self.register_pull()
        self.register_push()
        self.register_sources()
        self.register_srpm()
        self.register_switch_branch()
        self.register_tag()
        self.register_unused_patches()
        self.register_upload()
        self.register_verify_files()
        self.register_verrel()

    def load_cmd(self):
        """This sets up the cmd object"""

        # load items from the config file
        items = dict(self.config.items(self.name, raw=True))

        # Read comma separated list of kerberos realms
        realms = [realm
                  for realm in items.get("kerberos_realms", '').split(',')
                  if realm]

        # Create the cmd object
        self._cmd = self.site.Commands(self.args.path,
                                       items.get('lookaside'),
                                       items.get('lookasidehash', 'sha512'),
                                       items.get('lookaside_cgi'),
                                       items.get('gitbaseurl', ''),
                                       items.get('anongiturl', ''),
                                       branchre='.*',
                                       kojiconfig='',
                                       build_client=None,
                                       user=self.args.user,
                                       quiet=self.args.q,
                                       realms=realms
                                       )

        self._cmd.module_name = self.args.module_name
        self._cmd.debug = self.args.debug
        self._cmd.verbose = self.args.v
        self._cmd.clone_config = items.get('clone_config')

    def register_make_source(self):
        make_source_parser = self.subparsers.add_parser(
            'make-source', help='Create Source0 from the '
            'content of the current working directory '
            'after downloading any external sources. '
            'The content must be of unpacked type.',
            description='Puts content of the current '
            'working directory into a gzip-compressed archive named '
            'according to Source0 filename as specfied in the .spec file. '
            'The content must be of unpacked type, otherwise no action is taken. '
            'Unpacked content is such that it contains a .spec file '
            'that references no present source or patch '
            '(typically it contains only Source0 being '
            'generated automatically) and there is at least '
            'one file not in the list of ignored content (README, '
            'README.md, sources, tito.props, hidden files, '
            '.spec file). Note that by invoking this command '
            'with --outdir ., the directory content becomes '
            '"packed".')
        make_source_parser.add_argument(
            '--spec', action='store', default=None,
            help='Path to the spec file. By default .spec file '
            'is autodiscovered.')
        make_source_parser.add_argument(
            '--outdir', default=os.getcwd(),
            help='Where to put the generated source. '
            'By default cwd.')
        make_source_parser.set_defaults(command=self.make_source)

    def tag(self):
        self.cmd._rpmdefines = self.cmd.rpmdefines + ["--define 'dist %nil'"]
        super(rpkgClient, self).tag()

    def make_source(self):
        self.cmd.sources()
        self.cmd._spec = self.args.spec
        self.cmd.make_source(self.args.outdir)

    def srpm(self):
        self.cmd.sources()
        self.cmd._spec = self.args.spec
        try:
            self.cmd.make_source()
        except NotUnpackedException:
            pass
        self.cmd.srpm(self.args.outdir)

    def copr_build(self):
        self.args.outdir = None
        super(rpkgClient, self).copr_build()

    def is_packed(self):
        self.cmd._spec = self.args.spec
        ts = rpm.ts()
        try:
            rpm.addMacro("_sourcedir", self.cmd.path)
            rpm_spec = ts.parseSpec(self.cmd.spec)
        except ValueError as e:
            raise RpmSpecParseException(str(e))

        if self.cmd.is_unpacked(self.cmd.path, rpm_spec.sources):
            self.log.info('No')
        else:
            self.log.info('Yes')

    def register_srpm(self):
        """Register the srpm target"""
        srpm_parser = self.subparsers.add_parser(
            'srpm', help='Create a source rpm',
            description='Create a source rpm out of '
            'packed or unpacked content. See '
            'make-sources for the description of the '
            'two content types and their recognition.')
        srpm_parser.add_argument(
            '--spec', action='store', default=None,
            help='Path to the spec file. By default .spec file '
            'is autodiscovered.')
        srpm_parser.add_argument(
            '--outdir', default=os.getcwd(),
            help='Where to put the generated srpm.')
        srpm_parser.set_defaults(command=self.srpm)

    def register_is_packed(self):
        """Determine whether the package content is packed or not"""
        is_packed_parser = self.subparsers.add_parser(
            'is-packed', help='Tell user whether content is packed',
            description='Determine whether the package content '
            'in the working directory is packed or unpacked '
            'and print that information to the screen.')
        is_packed_parser.add_argument(
            '--spec', action='store', default=None,
            help='Path to an alternative spec file. Note that '
            'whether the content is packed on unpacked depends '
            'also on Source and Patch definitions in the spec '
            'file as well as on the actual content in the '
            'working directory.')
        is_packed_parser.set_defaults(command=self.is_packed)

    def register_copr_build(self):
        """Register the copr-build target"""
        copr_parser = self.subparsers.add_parser(
            'copr-build', help='Build package in COPR',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
            Build package in COPR.

            Note: you need to have set up correct api key. For more information
            see API KEY section of copr-cli(1) man page.
            """)
        copr_parser.add_argument(
            '--spec', action='store', default=None,
            help='Path to the spec file. By default .spec file '
            'is autodiscovered.')
        copr_parser.add_argument(
            '--config', required=False,
            metavar='CONFIG', dest='copr_config',
            help="Path to an alternative Copr configuration file")
        copr_parser.add_argument(
            '--nowait', action='store_true', default=False,
            help="Don't wait on build")
        copr_parser.add_argument(
            'project', nargs=1, help='Name of the project in format USER/PROJECT')
        copr_parser.set_defaults(command=self.copr_build)
