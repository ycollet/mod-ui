# Makefile for mod-ui
# Supports standard DESTDIR-based staged installation (rpmbuild, packaging).
#
# Typical usage:
#   make                        # build the C shared library
#   make install PREFIX=/usr    # install everything under /usr
#   make install PREFIX=/usr DESTDIR=/tmp/staging   # staged (RPM) install
#   make clean
#
# On Fedora x86_64, Python arch-specific packages live under lib64:
#   make install PYTHON_SITEDIR=/usr/lib64/python3.x/site-packages

# ── Paths ─────────────────────────────────────────────────────────────────────

PREFIX     ?= /usr
BINDIR     ?= $(PREFIX)/bin
LIBDIR     ?= $(PREFIX)/lib
DATADIR    ?= $(PREFIX)/share
SYSCONFDIR ?= /etc

PYTHON       ?= python3
PYTHON_VER   := $(shell $(PYTHON) -c "import sys; print('{}.{}'.format(*sys.version_info[:2]))")
PYTHON_SITEDIR ?= $(LIBDIR)/python$(PYTHON_VER)/site-packages

APPNAME   = mod-ui
# /usr/lib/mod-ui — server.py, launch.py; placed here instead of BINDIR
# because they are not directly executable (called via wrapper scripts).
APPLIBDIR = $(LIBDIR)/$(APPNAME)
# Paths match mod/settings.py defaults (sys.prefix + '/share/mod/...')
HTMLDIR   = $(DATADIR)/mod/html
PBDIR     = $(DATADIR)/mod/default.pedalboard
# Installed as a user-level systemd service (no root required to start)
SVCDIR    = $(LIBDIR)/systemd/user
CONFDIR   = $(SYSCONFDIR)/$(APPNAME)
APPSDIR   = $(DATADIR)/applications
ICONDIR   = $(DATADIR)/icons/hicolor

DESTDIR  ?=

# sed substitution token map used for wrapper scripts and the service unit
SUBST = sed \
	-e 's|@PYTHON@|$(PYTHON)|g' \
	-e 's|@PREFIX@|$(PREFIX)|g' \
	-e 's|@BINDIR@|$(BINDIR)|g' \
	-e 's|@LIBDIR@|$(LIBDIR)|g' \
	-e 's|@DATADIR@|$(DATADIR)|g' \
	-e 's|@SYSCONFDIR@|$(SYSCONFDIR)|g' \
	-e 's|@APPLIBDIR@|$(APPLIBDIR)|g' \
	-e 's|@HTMLDIR@|$(HTMLDIR)|g' \
	-e 's|@PBDIR@|$(PBDIR)|g' \
	-e 's|@SVCDIR@|$(SVCDIR)|g' \
	-e 's|@CONFDIR@|$(CONFDIR)|g'

# ── Targets ───────────────────────────────────────────────────────────────────

.PHONY: all build clean install uninstall

all: build

build:
	$(MAKE) -C utils

clean:
	$(MAKE) -C utils clean
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} +

# ── install ───────────────────────────────────────────────────────────────────

install: build
	# ── Python package: mod ───────────────────────────────────────────────────
	install -d $(DESTDIR)$(PYTHON_SITEDIR)/mod/communication
	install -m 644 mod/__init__.py           $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/addressings.py        $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/bank.py               $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/control_chain.py      $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/development.py        $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/hmi.py                $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/host.py               $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/mod_protocol.py       $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/profile.py            $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/protocol.py           $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/recorder.py           $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/screenshot.py         $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/session.py            $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/settings.py           $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/tuner.py              $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/webserver.py          $(DESTDIR)$(PYTHON_SITEDIR)/mod/
	install -m 644 mod/communication/__init__.py $(DESTDIR)$(PYTHON_SITEDIR)/mod/communication/
	install -m 644 mod/communication/crypto.py   $(DESTDIR)$(PYTHON_SITEDIR)/mod/communication/
	install -m 644 mod/communication/device.py   $(DESTDIR)$(PYTHON_SITEDIR)/mod/communication/
	install -m 644 mod/communication/token.py    $(DESTDIR)$(PYTHON_SITEDIR)/mod/communication/

	# ── Python package: modtools ──────────────────────────────────────────────
	install -d $(DESTDIR)$(PYTHON_SITEDIR)/modtools
	install -m 644 modtools/__init__.py   $(DESTDIR)$(PYTHON_SITEDIR)/modtools/
	install -m 644 modtools/pedalboard.py $(DESTDIR)$(PYTHON_SITEDIR)/modtools/
	install -m 644 modtools/tempo.py      $(DESTDIR)$(PYTHON_SITEDIR)/modtools/
	install -m 644 modtools/utils.py      $(DESTDIR)$(PYTHON_SITEDIR)/modtools/
	install -m 755 utils/libmod_utils.so  $(DESTDIR)$(PYTHON_SITEDIR)/modtools/

	# ── Application scripts ───────────────────────────────────────────────────
	install -d $(DESTDIR)$(APPLIBDIR)
	install -m 644 server.py $(DESTDIR)$(APPLIBDIR)/
	install -m 644 launch.py $(DESTDIR)$(APPLIBDIR)/

	# ── HTML / static assets ─────────────────────────────────────────────────
	install -d $(DESTDIR)$(HTMLDIR)
	cp -r html/. $(DESTDIR)$(HTMLDIR)/
	find $(DESTDIR)$(HTMLDIR) -type d -exec chmod 755 {} +
	find $(DESTDIR)$(HTMLDIR) -type f -exec chmod 644 {} +

	# ── Default pedalboard ───────────────────────────────────────────────────
	install -d $(DESTDIR)$(PBDIR)
	cp -r default.pedalboard/. $(DESTDIR)$(PBDIR)/
	find $(DESTDIR)$(PBDIR) -type d -exec chmod 755 {} +
	find $(DESTDIR)$(PBDIR) -type f -exec chmod 644 {} +

	# ── Wrapper scripts in BINDIR ─────────────────────────────────────────────
	install -d $(DESTDIR)$(BINDIR)
	$(SUBST) scripts/mod-ui.in > $(DESTDIR)$(BINDIR)/mod-ui
	chmod 755 $(DESTDIR)$(BINDIR)/mod-ui
	$(SUBST) scripts/mod-ui-launch.in > $(DESTDIR)$(BINDIR)/mod-ui-launch
	chmod 755 $(DESTDIR)$(BINDIR)/mod-ui-launch

	# ── systemd user service ─────────────────────────────────────────────────
	install -d $(DESTDIR)$(SVCDIR)
	$(SUBST) systemd/mod-ui.service > $(DESTDIR)$(SVCDIR)/mod-ui.service
	chmod 644 $(DESTDIR)$(SVCDIR)/mod-ui.service

	# ── Environment config template ───────────────────────────────────────────
	install -d $(DESTDIR)$(CONFDIR)
	install -m 644 systemd/mod-ui.env $(DESTDIR)$(CONFDIR)/mod-ui.env

	# ── Desktop entry ────────────────────────────────────────────────────────
	install -d $(DESTDIR)$(APPSDIR)
	$(SUBST) desktop/mod-ui.desktop.in > $(DESTDIR)$(APPSDIR)/mod-ui.desktop
	chmod 644 $(DESTDIR)$(APPSDIR)/mod-ui.desktop

	# ── Icons (hicolor theme, sourced from the favicon set) ───────────────────
	# Sizes available in the source: 16, 32, 96, 192, and 405 (used as 256).
	install -d $(DESTDIR)$(ICONDIR)/16x16/apps
	install -m 644 html/img/favicon/favicon-16x16.png \
		$(DESTDIR)$(ICONDIR)/16x16/apps/mod-ui.png
	install -d $(DESTDIR)$(ICONDIR)/32x32/apps
	install -m 644 html/img/favicon/favicon-32x32.png \
		$(DESTDIR)$(ICONDIR)/32x32/apps/mod-ui.png
	install -d $(DESTDIR)$(ICONDIR)/96x96/apps
	install -m 644 html/img/favicon/favicon-96x96.png \
		$(DESTDIR)$(ICONDIR)/96x96/apps/mod-ui.png
	install -d $(DESTDIR)$(ICONDIR)/192x192/apps
	install -m 644 html/img/favicon/android-icon-192x192.png \
		$(DESTDIR)$(ICONDIR)/192x192/apps/mod-ui.png
	install -d $(DESTDIR)$(ICONDIR)/256x256/apps
	install -m 644 html/img/favicon/favicon.png \
		$(DESTDIR)$(ICONDIR)/256x256/apps/mod-ui.png

# ── uninstall ─────────────────────────────────────────────────────────────────

uninstall:
	rm -rf $(DESTDIR)$(PYTHON_SITEDIR)/mod
	rm -rf $(DESTDIR)$(PYTHON_SITEDIR)/modtools
	rm -rf $(DESTDIR)$(APPLIBDIR)
	rm -rf $(DESTDIR)$(HTMLDIR)
	rm -rf $(DESTDIR)$(PBDIR)
	rm -f  $(DESTDIR)$(BINDIR)/mod-ui
	rm -f  $(DESTDIR)$(BINDIR)/mod-ui-launch
	rm -f  $(DESTDIR)$(SVCDIR)/mod-ui.service
	rm -f  $(DESTDIR)$(APPSDIR)/mod-ui.desktop
	rm -f  $(DESTDIR)$(ICONDIR)/16x16/apps/mod-ui.png
	rm -f  $(DESTDIR)$(ICONDIR)/32x32/apps/mod-ui.png
	rm -f  $(DESTDIR)$(ICONDIR)/96x96/apps/mod-ui.png
	rm -f  $(DESTDIR)$(ICONDIR)/192x192/apps/mod-ui.png
	rm -f  $(DESTDIR)$(ICONDIR)/256x256/apps/mod-ui.png
