# Minimal makefile for Sphinx documentation
#

SPHINXOPTS    ?= -W --keep-going
SPHINXBUILD  ?= sphinx-build
SOURCEDIR    = .
BUILDDIR     = ../build

# Get version from package
VERSION := $(shell python -c "import sys; sys.path.insert(0, '..'); import ecpet; print(ecpet._version.__release__)" 2>/dev/null || echo "unknown")

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)


.PHONY: help Makefile clean html pdf all

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)


# Custom targets
clean:
	rm -rf $(BUILDDIR)/*

html:
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS)

	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

pdf:
	$(SPHINXBUILD) -b latex $(SOURCEDIR) $(BUILDDIR)/latex $(SPHINXOPTS)
	@echo "Running LaTeX files through pdflatex..."
	$(MAKE) -C $(BUILDDIR)/latex all-pdf
	@mkdir -p $(BUILDDIR)/pdf
	@cp $(BUILDDIR)/latex/*.pdf $(BUILDDIR)/pdf/
	@echo "pdflatex finished; the PDF files are in $(BUILDDIR)/pdf."

clean:
	rm -rf $(BUILDDIR)/*

gitlabpages: html
	@echo "HTML build complete for GitLab Pages deployment."
