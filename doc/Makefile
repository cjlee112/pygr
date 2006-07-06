PWD=$(shell pwd)
PYTHON=$(shell python)
TEXINPUTS=$(PWD)/commontex:

MKHOWTO=   TEXINPUTS=$(TEXINPUTS) $(PWD)/tools/mkhowto
MKHTML = $(MKHOWTO) --html --about html/stdabout.dat \
                --iconserver icons --favicon icons/pyfav.png \
                --address $(PYTHONDOCS) 

PYTHONDOCS="See <i><a href=\"about.html\">About this document...</a></i> for information on suggesting changes."

pygr: html/pygr/pygr.html 
html/pygr/pygr.html: $(PYGRFILES) perl/distutils.perl 
	$(MKHTML) --dir html/pygr --split 4 pygr/pygr.tex

clean:	
	rm -rf html/pygr/*.html 
	rm -rf html/pygr/*.css
	rm -rf html/pygr/*.pl
	rm -rf html/pygr/*.dat
  
