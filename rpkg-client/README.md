This application is an RPM packaging utility based on python-rpkg library. It works with both [DistGit](https://github.com/release-engineering/dist-git)
and Git repositories and it handles two types of directory content: _packed_ content and _unpacked_ content.

- Packed (unexpanded) content is that composed of tarballs, patches, and a .spec file.
- Unpacked (expanded) content is that composed of plain source files and a .spec file.

For packed content, if you ask `rpkg` to make srpm (`rpkg srpm`), it will download any external
files from the appropriate storage (e.g. lookaside cache for DistGit) and then it will invoke
`rpmbuild -bs` with `_sourcedir`, `_specdir`, `_builddir`, `_srcrpmdir`,`_rpmdir` macros all
set to the working directory.

For unpacked content, if you ask `rpkg` to do the same thing, it will download external sources (if any)
and then it will also generate a tarball from the whole content of the working directory named according
to `Source0` definition present in the associated .spec file. This tarball and the .spec are then passed
to the same rpmbuild command as above for the packed content.

Note that by dynamically creating the tarball in the working directory according to the `Source0`
definition, the directory content becomes packed because there is at least one file, which is referenced
from the .spec file as `Source` or `Patch`. You can find the exact definitions of "packed" and "unpacked"
in `rpkg` man pages (see PACKED VS UNPACKED section for examples) or with `rpkg make-source --help`.

Apart from generating srpms from the application sources, you can also run other useful packaging commands
like `rpkg lint` to check the .spec file and the overall package conformance to RPM standard, `rpkg local`
to locally build the package into an rpm, or `rpkg copr-build` to build an srpm and send it for build to
[COPR](https://copr.fedorainfracloud.org).

Examples:
```
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
```
```
    $ cd prep-example
    $ ls .
    doc  LICENSE  README.md  rpkg  rpkg.bash  rpkg-client.spec  rpkg.conf  rpkglib  run_tests.sh  setup.py  tests
    $ rpkg make-source
    Wrote: rpkg-client/rpkg-client-0.8.tar.gz
    $ rpkg prep
    Executing(%prep): /bin/sh -e /var/tmp/rpm-tmp.bd5cCF
    + umask 022
    ...
    $ rpkg clean
```

You can find more information and more examples in rpkg man pages (`man rpkg`).
