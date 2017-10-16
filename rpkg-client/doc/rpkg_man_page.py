# Print a man page from the help texts.
#
# Copyright (C) 2011 Red Hat Inc.
# Author(s): Jesse Keating <jkeating@redhat.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.


import os
import sys
import datetime


# We could substitute the "" in .TH with the rpkg version if we knew it
man_header = """\
.\\" man page for rpkg
.TH rpkg 1 "%(today)s" "" "rpm\\-packager"
.SH "NAME"
rpkg \\- RPM Packaging utility
.SH "SYNOPSIS"
.B "rpkg"
[
.I global_options
]
.I "command"
[
.I command_options
]
[
.I command_arguments
]
.br
.B "rpkg"
.B "help"
.br
.B "rpkg"
.I "command"
.B "\\-\\-help"
.SH "DESCRIPTION"
.B "rpkg"
is a script to maintain RPM package content. It is designed to work with expanded sources as well
as with tarballs and patches. Note that you should trust the .spec files you work with because
many operations (like `rpkg srpm`, `rpkg lint`, or `rpkg is-packed`) involve parsing the spec file,
which brings along evalution of any shell or lua scriplets.
"""

man_footer = """\
.SH "EXAMPLES"

    $ cd prep-example
    $ ls .
    doc  LICENSE  README.md  rpkg  rpkg.bash  rpkg-client.spec  rpkg.conf  rpkglib  run_tests.sh  setup.py  tests
    $ rpkg prep
    error: File rpkg-client/rpkg-client-0.8.tar.gz: No such file or directory
    $ rpkg make-source
    Wrote: rpkg-client/rpkg-client-0.8.tar.gz
    $ rpkg prep
    Executing(%prep): /bin/sh -e /var/tmp/rpm-tmp.bd5cCF
    + umask 022
    ...
    $ rpkg clean

    In this example, we run prep phase of rpmbuild process in an originally unpacked directory. At first we get
    an error about the tarball not being present. We first need to run `rpkg make-source` manually to create it
    (which makes the working directory content "packed" by the way). Then `rpkg prep` can be successfully executed.
    The following applies also to `rpkg local` and `rpkg install`. In the end, the generated tarball can be removed
    with `rpkg clean` if the working directory is a Git repo.

    $ cd unpacked-copr-build-example
    $ ls .
    doc  LICENSE  README.md  rpkg  rpkg.bash  rpkg-client.spec  rpkg.conf  rpkglib  run_tests.sh  setup.py  tests
    $ rpkg copr-build user/project
    Wrote: copr-build-example/rpkg-client-0.8.tar.gz
    Wrote: copr-build-example/rpkg-client-0.8-1.fc25.src.rpm
    Uploading package rpkg-client-0.8-1.fc25.src.rpm
    100% |################################| 49kB 263kB/s eta 0:00:00
    Build was added to example:
      https://copr.fedorainfracloud.org/coprs/build/625402/
    Created builds: 625402
    ...

    This example illustrates launching a COPR build directly from an unpacked (expanded) content.
    SRPM is first build and then sent to COPR with copr-cli tool.

.SH "PACKED VS UNPACKED"

While it is quite intuitive what is packed content (.spec + tarballs + patches)
and what is unpacked content (.spec + original application source files), it
might be useful to know how exactly rpkg differentiates between these two.
You can go through the following examples to get overview how this tool exactly
works.

.SS PACKED CONTENT:

    $ cd source0-present-example
    $ grep -E '(Source|Patch)' testpkg.spec
    Source0: foo.tar.gz
    $ ls .
    foo.tar.gz testpkg.spec
    $ rpkg make-source
    Could not execute make_source: Not an unpacked content.
    $ rpkg srpm
    Failed to get module name from Git url or pushurl.
    Wrote: source0-present-example/testpkg-1-1.fc25.src.rpm

    The error about module name is caused by running `rpkg`
    on a plain directory content and not a Git repo. In this
    case module name is read out from the spec file. The
    error about not being able to make source is expected for
    packed content (tarballs to be put into srpm are expected
    to be present already).

    $ cd only-ignored-files-example
    $ grep -E '(Source|Patch)' testpkg.spec
    Source0: https://example.org/foo.tar.gz
    $ ls .
    README.md testpkg.spec
    $ rpkg make-source
    Could not execute make_source: Not an unpacked content.
    $ echo '%_disable_source_fetch 0' >> ~/.rpmmacros
    $ rpkg srpm
    Failed to get module name from Git url or pushurl
    warning: Downloading https://example.org/foo.tar.gz to only-ignored-files-example/foo.tar.gz
    Wrote: only-ignored-files-example/testpkg-1-1.fc25.src.rpm

    In this example, sources are downloaded from network when
    srpm is being built. The %_disable_source_fetch rpm macro
    must be set to 0 and the tarball url must be valid for this
    to work. The content is recognized as packed because there
    are only ignored files in the directory (.spec and readmes).

.SS UNPACKED CONTENT:

    $ cd cpp-source-file-present-example
    $ git init .
    $ git remote add origin https://github.com/testpkg.git
    $ grep -E '(Source|Patch)' testpkg.spec
    Source0: foo.tar.gz
    $ ls .
    main.cpp testpkg.spec
    $ rpkg make-source
    Wrote: cpp-source-file-present-example/foo.tar.gz
    $ rpkg srpm
    Wrote: cpp-source-file-present-example/testpkg-1-1.fc25.src.rpm

    foo.tar.gz (the only Source referenced from the .spec file) is
    not present and there is unignored main.cpp file that makes the
    content recognized as unpacked. When `rpkg make-source` is invoked,
    foo.tar.gz is created and will contain the main.cpp file (as
    well as the .spec metadata file but that is just because the
    whole content directory is packed). Note that the error about
    failing to get module name from Git url disappeared because
    we have run `git init .` and `git remote add ...`.

.SH "SEE ALSO"
.UR "https://pagure.io/rpkg-client/"
.BR "https://pagure.io/rpkg-client/"
"""


class ManFormatter(object):
    def __init__(self, man):
        self.man = man

    def write(self, data):
        for line in data.split('\n'):
            self.man.write('  %s\n' % line)


def strip_usage(s):
    """Strip "usage: " string from beginning of string if present"""
    if s.startswith('usage: '):
        return s.replace('usage: ', '', 1)
    else:
        return s


def man_constants():
    """Global constants for man file templates"""
    today = datetime.date.today()
    today_manstr = today.strftime(r'%Y\-%m\-%d')
    return {'today': today_manstr}


def generate(parser, subparsers):
    """\
    Generate the man page on stdout

    Given the argparse based parser and subparsers arguments, generate
    the corresponding man page and write it to stdout.
    """

    # Not nice, but works: Redirect any print statement output to
    # stderr to avoid clobbering the man page output on stdout.
    man_file = sys.stdout
    sys.stdout = sys.stderr

    mf = ManFormatter(man_file)

    choices = subparsers.choices
    k = sorted(choices.keys())

    man_file.write(man_header % man_constants())

    helptext = parser.format_help()
    helptext = strip_usage(helptext)
    helptextsplit = helptext.split('\n')
    helptextsplit = [line for line in helptextsplit
                     if not line.startswith('  -h, --help')]

    man_file.write('.SS "%s"\n' % ("Global Options",))

    outflag = False
    for line in helptextsplit:
        if line == "optional arguments:":
            outflag = True
        elif line == "":
            outflag = False
        elif outflag:
            man_file.write("%s\n" % line)

    help_texts = {}
    for pa in subparsers._choices_actions:
        help_texts[pa.dest] = getattr(pa, 'help', None)

    man_file.write('.SH "COMMAND OVERVIEW"\n')

    for command in k:
        cmdparser = choices[command]
        if not cmdparser.add_help:
            continue
        usage = cmdparser.format_usage()
        usage = strip_usage(usage)
        usage = ''.join(usage.split('\n'))
        usage = ' '.join(usage.split())
        if help_texts[command]:
            man_file.write('.TP\n.B "%s"\n%s\n' % (usage, help_texts[command]))
        else:
            man_file.write('.TP\n.B "%s"\n' % (usage))

    man_file.write('.SH "COMMAND REFERENCE"\n')
    for command in k:
        cmdparser = choices[command]
        if not cmdparser.add_help:
            continue

        man_file.write('.SS "%s"\n' % cmdparser.prog)

        help = help_texts[command]
        if help and not cmdparser.description:
            if not help.endswith('.'):
                help = "%s." % help
            cmdparser.description = help

        h = cmdparser.format_help()
        mf.write(h)

    man_file.write(man_footer)


if __name__ == '__main__':
    module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, module_path)

    from rpkglib.cli import rpkgClient
    client = rpkgClient(name='rpkg', config=None)
    client.do_imports('rpkglib')

    generate(client.parser, client.subparsers)
