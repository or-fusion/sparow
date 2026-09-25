# Makefile for Sphinx documentation

# You can set these variables from the command line.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Clean build directory
clean:
	rm -rf "$(BUILDDIR)"

# HTML documentation
html:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

# Check for broken links
linkcheck:
	$(SPHINXBUILD) -b linkcheck "$(SOURCEDIR)" "$(BUILDDIR)/linkcheck" $(SPHINXOPTS)
	@echo
	@echo "Link check complete; look for any errors in the above output "
	@echo "or in $(BUILDDIR)/linkcheck/output.txt."

# Build documentation with coverage check
coverage:
	$(SPHINXBUILD) -b coverage "$(SOURCEDIR)" "$(BUILDDIR)/coverage" $(SPHINXOPTS)
	@echo
	@echo "The coverage check output is in $(BUILDDIR)/coverage."
	@echo "Check the HTML files in that directory for missing documentation."

# Build documentation in LaTeX format
latex:
	$(SPHINXBUILD) -b latex "$(SOURCEDIR)" "$(BUILDDIR)/latex" $(SPHINXOPTS)
	@echo
	@echo "Running LaTeX files..."
	make -C "$(BUILDDIR)/latex" all-pdf
	@echo
	@echo "Build finished; the PDF files are in $(BUILDDIR)/latex."

# Build documentation in text format
text:
	$(SPHINXBUILD) -b text "$(SOURCEDIR)" "$(BUILDDIR)/text" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The text files are in $(BUILDDIR)/text."

# Build man pages
man:
	$(SPHINXBUILD) -b man "$(SOURCEDIR)" "$(BUILDDIR)/man" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The manual pages are in $(BUILDDIR)/man."

# Build Texinfo files
texinfo:
	$(SPHINXBUILD) -b texinfo "$(SOURCEDIR)" "$(BUILDDIR)/texinfo" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The Texinfo files are in $(BUILDDIR)/texinfo."
	@echo "Run 'make' in that directory to run these through makeinfo"
	@echo "(use 'make info' here to do that automatically)."

# Build Info files
info:
	$(SPHINXBUILD) -b texinfo "$(SOURCEDIR)" "$(BUILDDIR)/texinfo" $(SPHINXOPTS)
	@echo "Running Texinfo files through makeinfo..."
	make -C "$(BUILDDIR)/texinfo" info
	@echo
	@echo "Build finished. The Info files are in $(BUILDDIR)/texinfo."

# Build gettext catalogs
gettext:
	$(SPHINXBUILD) -b gettext "$(SOURCEDIR)" "$(BUILDDIR)/locale" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The message catalogs are in $(BUILDDIR)/locale."

# Build changes overview
changes:
	$(SPHINXBUILD) -b changes "$(SOURCEDIR)" "$(BUILDDIR)/changes" $(SPHINXOPTS)
	@echo
	@echo "The overview file is in $(BUILDDIR)/changes."

# Build XML files
xml:
	$(SPHINXBUILD) -b xml "$(SOURCEDIR)" "$(BUILDDIR)/xml" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The XML files are in $(BUILDDIR)/xml."

# Build pseudoxml files
pseudoxml:
	$(SPHINXBUILD) -b pseudoxml "$(SOURCEDIR)" "$(BUILDDIR)/pseudoxml" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The pseudo-XML files are in $(BUILDDIR)/pseudoxml."

# Build JSON files
json:
	$(SPHINXBUILD) -b json "$(SOURCEDIR)" "$(BUILDDIR)/json" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The JSON files are in $(BUILDDIR)/json."

# Build HTML help files
htmlhelp:
	$(SPHINXBUILD) -b htmlhelp "$(SOURCEDIR)" "$(BUILDDIR)/htmlhelp" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The HTML help files are in $(BUILDDIR)/htmlhelp."

# Build Apple Help files
applehelp:
	$(SPHINXBUILD) -b applehelp "$(SOURCEDIR)" "$(BUILDDIR)/applehelp" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The Apple Help files are in $(BUILDDIR)/applehelp."

# Build DevHelp files
devhelp:
	$(SPHINXBUILD) -b devhelp "$(SOURCEDIR)" "$(BUILDDIR)/devhelp" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The DevHelp files are in $(BUILDDIR)/devhelp."

# Build Epub files
epub:
	$(SPHINXBUILD) -b epub "$(SOURCEDIR)" "$(BUILDDIR)/epub" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The Epub file is in $(BUILDDIR)/epub."

# Build Epub3 files
epub3:
	$(SPHINXBUILD) -b epub3 "$(SOURCEDIR)" "$(BUILDDIR)/epub3" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The Epub3 file is in $(BUILDDIR)/epub3."

# Build Qt Help files
qthelp:
	$(SPHINXBUILD) -b qthelp "$(SOURCEDIR)" "$(BUILDDIR)/qthelp" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The Qt Help files are in $(BUILDDIR)/qthelp."
	@echo "Run 'qcollectiongenerator' on the .qhcp project file to"
	@echo "create a .qhc file for use with Qt Assistant."

# Build quick reference
quickstart:
	$(SPHINXBUILD) -b quickstart "$(SOURCEDIR)" "$(BUILDDIR)/quickstart" $(SPHINXOPTS)
	@echo
	@echo "Build finished. The quickstart files are in $(BUILDDIR)/quickstart."