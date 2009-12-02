

def catalog_downloads(url, fileFilter, fileNamer, fileDocumenter, klass):
    '''returns dict of resources for downloading target data:
    url: URL to a directory that gives links to the desired data
    fileFilter: function that returns True for a desired file name
    fileNamer: function that converts a file name into desired key value
    fileDocumenter: function that returns a docstring based on file name
    klass: a Python class or function that takes file URL as a single argument,
           and returns value to store in dictionary

    example usage:
    d = catalog_downloads("http://biodb.bioinformatics.ucla.edu/PYGRDATA/",
                          lambda x: x.endswith(".txt.gz"),
                          lambda x: "Bio.MSA.UCSC."+x[:-3],
                          SourceURL)
    '''
    import formatter
    import htmllib
    import urllib
    #from BeautifulSoup import BeautifulSoup
    ifile = urllib.urlopen(url)
    try:
        p = htmllib.HTMLParser(formatter.NullFormatter())
        p.feed(ifile.read())
        l = p.anchorlist
        #soup = BeautifulSoup(ifile.read())
        # l = [str(a['href']) for a in soup.findAll('a')]
    finally:
        ifile.close()
    d = {}
    if url[-1] != '/': # make sure url ends in trailing /
        url += '/'
    for s in l: # find all anchors in the document
        if fileFilter(s): # save it
            o = klass(urllib.basejoin(url, s))
            o.__doc__ = fileDocumenter(s)
            d[fileNamer(s)] = o
    return d


def save_NLMSA_downloaders(url, fileFilter=lambda x: x.endswith(".txt.gz"),
                           resourceStem='Bio.MSA.UCSC.',
                           fileDocumenter=None, fileNamer=None):
    '''save NLMSA downloader / builder objects for a set
    of downloadable textdump files'''
    if fileDocumenter is None:
        fileDocumenter = lambda x: 'NLMSA alignment ' + x
    if fileNamer is None: # a default resource naming function
        fileNamer = lambda x: resourceStem + x[:-3] # remove .gz suffix
    from pygr.nlmsa_utils import NLMSABuilder
    from pygr.downloader import SourceURL
    d = catalog_downloads(url, fileFilter, fileNamer,
                          fileDocumenter, SourceURL)
    for resID, o in d.items():
        nlmsa = NLMSABuilder(o)
        nlmsa.__doc__ = fileDocumenter(resID)
        d[resID[:-4]] = nlmsa # remove .txt suffix
    from pygr import worldbase
    worldbase.add_resource(d)
    worldbase.commit()
    return d # just in case the user wants to see what was saved
