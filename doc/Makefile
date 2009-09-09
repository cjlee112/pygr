DOC_DIR=rest
BUILD_DIR=html_new
EPYDOC_DIR=$(BUILD_DIR)/epydoc


all: newdocs

newdocs:
	-mkdir -p $(BUILD_DIR)
	sphinx-build -b html $(DOC_DIR) $(BUILD_DIR)

epydocs:
	rm -rf $(EPYDOC_DIR)
	-mkdir -p $(EPYDOC_DIR)
	epydoc --docformat restructuredtext ../pygr -o $(EPYDOC_DIR)

clean:
	rm -rf html_new/ 

