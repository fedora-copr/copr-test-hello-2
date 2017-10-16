Name: rpkg-client
Version: 0.10
Release: 1%{?dist}
Summary: RPM packaging utitility
License: GPLv2+
URL: https://pagure.io/rpkg-client.git

# How to obtain the sources
# git clone https://pagure.io/rpkg-client.git
# cd rpkg-client
# tito build --tgz
Source0: %{name}-%{version}.tar.gz

BuildArch: noarch

%description
This package contains the rpkg utility. We are putting
the actual 'rpkg' package into a subpackage because there already exists package
https://admin.fedoraproject.org/pkgdb/package/rpms/rpkg. This package, however,
does not actually produce rpkg rpm, which this package does.

%package -n rpkg
Summary: RPM packaging utitility
BuildArch: noarch

BuildRequires: python
BuildRequires: python-setuptools
BuildRequires: python-devel
BuildRequires: python2-rpkg
BuildRequires: python2-mock

%if 0%{?rhel}
BuildRequires: pytest
%else
BuildRequires: python2-pytest
%endif

Requires: python2-rpkg

%description -n rpkg
This is an RPM packaging utility based on python-rpkg library.
It works with both DistGit and standard Git repositories and it handles
packed directory content as well as unpacked content. update

%prep
%setup -q

%check
./run_tests.sh

%build
%py2_build
%{__python2} doc/rpkg_man_page.py > rpkg.1

%install
%py2_install
install -d %{buildroot}%{_mandir}/man1
install -p -m 0644 rpkg.1 %{buildroot}%{_mandir}/man1

install -d %{buildroot}%{_sysconfdir}
install -d %{buildroot}%{_datarootdir}/bash-completion/completions

cp -a rpkg.conf %{buildroot}%{_sysconfdir}/
cp -a rpkg.bash %{buildroot}%{_datarootdir}/bash-completion/completions/

%files -n rpkg
%license LICENSE
%{python2_sitelib}/*

%config(noreplace) %{_sysconfdir}/rpkg.conf
%{_datadir}/bash-completion/completions/rpkg.bash

%{_bindir}/rpkg
%{_mandir}/*/*

%changelog
* Mon Oct 16 2017 clime <clime@redhat.com> 0.9-1
- update spec descriptions
- added is-packed subcommand
- try reading ~/.config/rpkg before /etc/rpkg
- add unittests
- for source downloading, try both url formats
  with/without hashtype
- add make-source subcommand
- patch srpm to generate Source0 if unpacked content
- override load_ns_module_name to work with any length
  namespaces
- added --spec for srpm, make-source, and copr-build
- fixed tagging not to include host dist tag
- docs update
- make all config values optional

* Thu Jul 27 2017 clime <clime@redhat.com> 0.8-1
- fix man pages to only include actually provided part of pyrpkg functionality
- add rpkglib to provide functional interface
- change summary of wrapper package

* Wed Jul 26 2017 clime <clime@redhat.com> 0.7-1
- use %%py2_build and %%py2_install macros
- explicitly invoke python2 for doc generation
- remove no longer needed $BUILDROOT removal in %%install clause
- add missing BuildRequires on python-setuptools

* Fri Jul 07 2017 clime <clime@redhat.com> 0.6-1
- fix build error

* Tue Jun 27 2017 clime <clime@redhat.com> 0.5-1
- remove Requires bash-completion

* Tue Jun 27 2017 clime <clime@redhat.com> 0.4-1
- move config file to /etc/rpkg.conf
- add Requires bash-completion

* Tue Jun 27 2017 clime <clime@redhat.com> 0.3-1
- remove some directories from %%files in .spec
- add (for now) short README.md

* Tue Jun 20 2017 clime <clime@redhat.com> 0.2-1
- new rpkg-client package built with tito

* Mon Jun 12 2017 clime <clime@redhat.com> 0.1-1
- Initial version
