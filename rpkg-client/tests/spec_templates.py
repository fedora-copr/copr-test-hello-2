from string import Template

SPEC_TEMPLATE = Template("""
Name:       $pkgname
Version:    1
Release:    1
Summary:    This is a test package.

License:    GPLv2+
URL:        https://someurl.org
Source0:    $source0

%description
""")

SPEC_WITH_PATCH_TEMPLATE = Template("""
Name:       $pkgname
Version:    1
Release:    1
Summary:    This is a test package.

License:    GPLv2+
URL:        https://someurl.org
Source0:    $source0

Patch0:     $patch0

%description
""")

INVALID_SPEC_TEMPLATE = Template("""
Name:       $pkgname
Version:    1
Release:    1
Summary:    This is a test package.

License:    GPLv2+
URL:        https://someurl.org
""")

NO_SOURCE_ZERO_SPEC_TEMPLATE = Template("""
Name:       $pkgname
Version:    1
Release:    1
Summary:    This is a test package.

License:    GPLv2+
URL:        https://someurl.org

%description
""")
