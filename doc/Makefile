PWD=$(shell pwd)
PYTHON=$(shell python)
TEXINPUTS=$(PWD)/commontex:

MKHOWTO=   TEXINPUTS=$(TEXINPUTS) $(PWD)/tools/mkhowto
MKHTML = $(MKHOWTO) --html --about html/stdabout.dat \
                --iconserver icons --favicon icons/pyfav.png \
                --address $(PYTHONDOCS) 

PYTHONDOCS="See <i><a href=\"about.html\">About this document...</a></i> for information on suggesting changes."

DOC_DIR=rest
BUILD_DIR=html_new
EPYDOC_DIR=$(BUILD_DIR)/epydoc

all: newdocs

pygr: html/pygr/pygr.html 
html/pygr/pygr.html: $(PYGRFILES) perl/distutils.perl 
	$(MKHTML) --dir html/pygr --split 4 pygr/pygr.tex

newdocs:
	sphinx-build -b html $(DOC_DIR) $(BUILD_DIR)

epydocs:
	rm -rf $(EPYDOC_DIR)
	epydoc --docformat restructuredtext ../pygr -o $(EPYDOC_DIR)

clean:	
	rm -rf html/pygr/*.html 
	rm -rf html/pygr/*.css
	rm -rf html/pygr/*.pl
	rm -rf html/pygr/*.dat
  
