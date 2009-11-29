
import types


# STORES DICTIONARY OF ATTRIBUTE-BOUND GRAPHS
# AND LIST OF UNBOUND GRAPHS
class SchemaDict(dict):
    """Container for schema rules bound to a class or object. Rules
    are stored in two indexes for fast access, indexed by graph, and
    indexed by attrname. Use += and -= to add or remove rules.
    """

    def __init__(self, newlist=(), baselist=()):
        "Initialize schema list from list of base classes and newlist of rules"
        self.attrs = {}
        dict.__init__(self)
        # COMBINE SCHEMAS FROM PARENTS WITH NEW SCHEMA LIST
        for b in baselist:
            if hasattr(b, '__class_schema__'):
                self.update(b.__class_schema__)
                self.attrs.update(b.__class_schema__.attrs)
        for i in newlist: # newlist OVERRIDES OLD DEFS FROM baselist
            self += i

    def __iadd__(self, i):
        "Add a schema rule to this SchemaDict"
        g = i[0]
        if len(i) >= 2:
            if isinstance(i[1], types.StringType):
                if i[1] in self.attrs: # REMOVE OLD ENTRY
                    self -= self.attrs[i[1]]
                self.attrs[i[1]] = i # SAVE IN INDEX ACCORDING TO ATTR NAME
            else:
                raise TypeError('Attribute name must be a string')
        if g not in self:
            self[g] = []
        self[g].append(i) # SAVE IN GRAPH INDEX
        return self # REQUIRED FROM iadd()!!

    def __isub__(self, i):
        "Remove a schema rule from this SchemaDict"
        g = i[0]
        if g not in self:
            raise KeyError('graph not found in SchemaDict!')
        self[g].remove(i) # REMOVE OLD ENTRY
        if len(self[g]) == 0: # REMOVE EMPTY LIST
            del self[g]
        if len(i) >= 2:
            if isinstance(i[1], types.StringType):
                if i[1] not in self.attrs:
                    raise KeyError('attribute not found in SchemaDict!')
                del self.attrs[i[1]] # REMOVE OLD ENTRY
            else:
                raise TypeError('Attribute name must be a string')
        return self # REQUIRED FROM iadd()!!

    def initInstance(self, obj):
        "Add obj as new node to all graphs referenced by this SchemaDict."
        for g, l in self.items(): # GET ALL OUR RULES
            for s in l:
                if obj not in g:
                    g.__iadd__(obj, (s, ))  # ADD OBJECT TO GRAPH USING RULE s

    def getschema(self, attr=None, graph=None):
        "Return list of schema rules that match attr / graph arguments."
        if attr:
            if attr in self.attrs:
                return [self.attrs[attr]]
        elif graph:
            if graph in self:
                return self[graph]
        else:
            raise ValueError('You must specify an attribute or graph.')
        return [] # DIDN'T FIND ANYTHING


class SchemaList(list):
    "Temporary container for returned schema list, with attached methods"

    def __init__(self, obj):
        self.obj = obj # OBJECT THAT WE'RE DESCRIBING SCHEMA OF
        list.__init__(self) # CALL SUPERCLASS CONSTRUCTOR

    def __iadd__(self, rule):
        "Add a new schema rule to object described by this SchemaList"
        if not hasattr(self.obj, '__schema__'):
            self.obj.__schema__ = SchemaDict()
        self.obj.__schema__ += rule
        return self # REQUIRED FROM iadd()!!

    # PROBABLY NEED AN __isub__() TOO??


######################
# getschema, getnodes, getedges
# these functions are analogous to getattr, except they get graph information

def getschema(o, attr=None, graph=None):
    "Get list of schema rules for object o that match attr / graph arguments."
    found = SchemaList(o)
    attrs = {}
    if hasattr(o, '__schema__'):
        for s in o.__schema__.getschema(attr, graph):
            found.append(s)
            if isinstance(s[1], types.StringType):
                attrs[s[1]] = None
    if attr and len(found) > 0: # DON'T PROCEED
        return found
    if hasattr(o, '__class_schema__'):
        for s in o.__class_schema__.getschema(attr, graph):
            if not isinstance(s[1], types.StringType) or s[1] not in attrs:
                found.append(s) # DON'T OVERWRITE OBJECT __schema__ BINDINGS
    return found


def setschema(o, attr, graph):
    """Bind object to graph, and if attr not None, also bind graph
    to this attribute."""
    if not hasattr(o, '__schema__'):
        o.__schema__ = SchemaDict()
    o.__schema__ += (graph, attr)


def getnodes(o, attr=None, graph=None):
    """Get destination nodes from graph bindings of o, limited to the
    specific attribute or graph if specified"""
    if attr:
        if hasattr(o, '__schema__') and attr in o.__schema__:
            return getattr(o, o.__schema__[attr][2]) # RETURN THE PRODUCT

        if hasattr(o, '__class_schema__') and attr in o.__class_schema__:
            return getattr(o, o.__class_schema__[attr][2]) # RETURN THE PRODUCT
        raise AttributeError('No attribute named %s in object %s' % (attr, o))
    elif graph: # JUST LOOK UP THE GRAPH TRIVIALLY
        return graph[o]
    else: # SHOULD WE GET ALL NODES FROM ALL SCHEMA ENTRIES?  HOW??
        raise ValueError('You must pass an attribute name or graph')


def getedges(o, attr=None, graph=None):
    """Get edges from graph bindings of o, limited to the specific attribute
    or graph if specified"""
    g = getnodes(o, attr, graph) # CAN JUST REUSE THE LOGIC OF getnodes
    if g and hasattr(g, 'edges'):
        return g.edges()
    else:
        return None
