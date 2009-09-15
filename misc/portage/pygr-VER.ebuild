# Copyright 1999-2009 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

NEED_PYTHON=2.3

inherit distutils

DESCRIPTION="A Python graph-database toolkit oriented primarily on bioinformatics applications"
HOMEPAGE="http://code.google.com/p/pygr/"
SRC_URI="http://pygr.googlecode.com/files/${P}.tar.gz"

LICENSE="BSD"
SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE="doc mysql sqlite"

DEPEND="doc? ( dev-python/sphinx )"
RDEPEND="mysql? ( dev-python/epydoc dev-python/mysql-python )
	sqlite? ( || ( dev-python/pysqlite >=dev-lang/python-2.5 ) )"

src_install() {
	distutils_src_install

	dodoc README.txt LICENSE.txt misc/pygrrc.example
	if use doc; then
		cd doc
		emake
		emake epydocs
		dohtml -r html_new/*
	fi
}

src_test() {
	"${python}" tests/runtest.py -b || die "Running tests failed"
}
