DOC_DIR=rest
BUILD_DIR=html_new
LATEX_DIR=latex_new
EPYDOC_DIR=$(BUILD_DIR)/epydoc

all: newdocs pdf

newdocs:
	-mkdir -p $(BUILD_DIR)
	sphinx-build -b html $(DOC_DIR) $(BUILD_DIR)

epydocs:
	rm -rf $(EPYDOC_DIR)
	-mkdir -p $(EPYDOC_DIR)
	epydoc --docformat restructuredtext ../pygr -o $(EPYDOC_DIR)

pdf:
	-mkdir -p $(LATEX_DIR)
	sphinx-build -b latex $(DOC_DIR) $(LATEX_DIR)
	make -C ./$(LATEX_DIR)
	cd ..
	echo "PDF is in: ./$(LATEX_DIR)/Pygr.pdf"

clean:
	rm -rf $(BUILD_DIR) $(LATEX_DIR)

