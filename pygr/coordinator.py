from __future__ import generators
import os
import time
import thread
import sys
import xmlrpclib
import traceback
from SimpleXMLRPCServer import SimpleXMLRPCServer
import socket

import dbfile
import logging


def get_hostname(host=None):
    'get FQDN for host, or current host if not specified'
    if host is None:
        host = socket.gethostname()
    try:
        return socket.gethostbyaddr(host)[0]
    except socket.herror: # DNS CAN'T RESOLVE HOSTNAME
        return host # JUST USE HOSTNAME AS REPORTED BY gethostname()


def get_server(host, port, logRequests=False):
    """Start xmlrpc server on requested host:port.

    Return bound SimpleXMLRPCServer server obj and port it's bound to.

    Set port=0 to bind to a random port number.
    """
    if host is None: # use localhost as default
        host = 'localhost'
    server = SimpleXMLRPCServer((host, port), logRequests=logRequests)
    port = server.socket.getsockname()[1]
    logging.info("Running XMLRPC server on port %d..." % port)
    return server, port


class XMLRPCClientObject(object):
    """provides object proxy for remote object,
    with methods that mirror its xmlrpc_methods"""

    def __init__(self, server, name, methodDict):
        self.name = name
        self.server = server
        import new

        class methodcall(object):

            def __init__(self, name):
                self.name = name

            def __call__(self, obj, *args):
                return obj.server.server.methodCall(obj.name, self.name, args)

        # Create methods to access those of the remote object.
        for methodName in methodDict:
            setattr(self, methodName, new.instancemethod(methodcall(
                methodName), self, self.__class__))


class XMLRPCClient(dict):
    'interface to XMLRPC server serving multiple named objects'

    def __init__(self, url):
        self.server = xmlrpclib.ServerProxy(url)

    def __getitem__(self, name):
        'get connection to the named server object'
        try:
            return dict.__getitem__(self, name)
        except KeyError:
            # Get information about the requested object.
            methodDict = self.server.objectInfo(name)
            import types
            if isinstance(methodDict, types.StringType):
                raise KeyError(methodDict) # RETURNED VALUE IS ERROR MESSAGE!
            v = XMLRPCClientObject(self, name, methodDict)
            self[name] = v # SAVE THIS OBJECT INTO OUR DICTIONARY
            return v


class ConnectionDict(dict):
    """ensure that multiple requests for the same connection
    use the same ServerProxy"""

    def __call__(self, url, name):
        try:
            s = self[url] # REUSE EXISTING CONNECTION TO THE SERVER
        except KeyError:
            s = XMLRPCClient(url) # GET NEW CONNECTION TO THE SERVER
            self[url] = s # CACHE THIS CONNECTION
        return s[name] # GET THE REQUESTED OBJECT PROXY FROM THE SERVER

get_connection = ConnectionDict() # THIS RETURNS SAME ServerProxy FOR SAME url


def safe_dispatch(self, name, args):
    """restrict calls to selected methods, and trap all exceptions to
    keep server alive!"""
    import datetime
    if name in self.xmlrpc_methods:
        # Make sure this method is explicitly allowed.
        try: # TRAP ALL ERRORS TO PREVENT OUR SERVER FROM DYING
            print >>sys.stderr, 'XMLRPC:', name, args, \
                  datetime.datetime.now().isoformat(' ') # LOG THE REQUEST
            if self.xmlrpc_methods[name]: # use this as an alias for method
                m = getattr(self, self.xmlrpc_methods[name])
            else: # use method name as usual
                m = getattr(self, name) # GET THE BOUND METHOD
            val = m(*args) # CALL THE METHOD
            sys.stderr.flush() # FLUSH ANY OUTPUT TO OUR LOG
            return val # HAND BACK ITS RETURN VALUE
        except SystemExit:
            raise  # WE REALLY DO WANT TO EXIT.
        except: # METHOD RAISED AN EXCEPTION, SO PRINT TRACEBACK TO STDERR
            traceback.print_exc(self.max_tb, sys.stderr)
    else:
        print >>sys.stderr, "safe_dispatch: blocked unregistered method %s" \
                % name
    return False # THIS RETURN VALUE IS CONFORMABLE BY XMLRPC...


class ObjectFromString(list):
    """convenience class for initialization from string of format:
    val1,val2,foo=12,bar=39,sshopts=-1 -p 1234
    Args of format name=val are saved on the object as attributes;
    otherwise each arg is saved as a list.
    Argument type conversion is performed automatically if attrtype
    mapping provided either to constructor or by the class itself.
    Numeric keys in this mapping are applied to the corresponding
    list arguments; string keys in this mapping are applied to
    the corresponding attribute arguments.
    Both the argument separator and assignment separator can be
    customized."""
    _separator = ','
    _eq_separator = '='

    def __init__(self, s, separator=None, eq_separator=None):
        list.__init__(self)
        if separator is None:
            separator = self._separator
        if eq_separator is None:
            eq_separator = self._eq_separator
        args = s.split(separator)
        i = 0
        for arg in args:
            try: # PROCESS attr=val ARGUMENT FORMAT
                k, v = arg.split(eq_separator)
                try: # SEE IF WE HAVE A TYPE FOR THIS ATTRIBUTE
                    v = self._attrtype[k](v)
                except (AttributeError, KeyError):
                    pass # IF NO CONVERSION, JUST USE THE ORIGINAL STRING
                setattr(self, k, v) # SAVE VALUE AS ATTRIBUTE
            except ValueError: # JUST A SIMPLE ARGUMENT, SO SAVE AS ARG LIST
                try: # SEE IF WE HAVE A TYPE FOR THIS LIST ITEM
                    arg = self._attrtype[i](arg)
                except (AttributeError, KeyError):
                    pass # IF NO CONVERSION, JUST USE THE ORIGINAL STRING
                self.append(arg)
                i += 1 # ADVANCE OUR ARGUMENT COUNT


class FileDict(dict):
    """read key,value pairs as WS-separated lines,
    with objclass(value) conversion"""

    def __init__(self, filename, objclass=str):
        dict.__init__(self)
        f = file(filename, 'rU') # text file
        for line in f:
            key = line.split()[0] # GET THE 1ST ARGUMENT
            # Get the rest, strip the outer whitespace.
            val = line[len(key):].lstrip().rstrip()
            self[key] = objclass(val) # APPLY THE DESIRED TYPE CONVERSION
        f.close()


def detach_as_demon_process(self):
    "standard UNIX technique c/o Jurgen Hermann's Python Cookbook recipe"
    # CREATE AN APPROPRIATE ERRORLOG FILEPATH
    if not hasattr(self, 'errlog') or self.errlog is False:
        self.errlog = os.path.join(os.getcwd(), self.name + '.log')
    pid = os.fork()
    if pid:
        return pid

    os.setsid() # CREATE A NEW SESSION WITH NO CONTROLLING TERMINAL
    os.umask(0) # IS THIS ABSOLUTELY NECESSARY?

    sys.stdout = file(self.errlog, 'a') # Daemon sends all output to log file.
    sys.stderr = sys.stdout
    return 0


def serve_forever(self):
    'start the service -- this will run forever'
    import datetime
    print >>sys.stderr, "START_SERVER:%s %s" % (self.name, datetime.datetime.
                                                now().isoformat(' '))
    sys.stderr.flush()
    self.server.serve_forever()


class CoordinatorInfo(object):
    """stores information about individual coordinators for the controller
    and provides interface to Coordinator that protects against possibility of
    deadlock."""
    min_startup_time = 60.0

    def __init__(self, name, url, user, priority, resources, job_id=0,
                 immediate=False, demand_ncpu=0):
        self.name = name
        self.url = url
        self.user = user
        self.priority = priority
        self.job_id = job_id
        self.immediate = immediate
        self.server = xmlrpclib.ServerProxy(url)
        self.processors = {}
        self.resources = resources
        self.start_time = time.time()
        self.demand_ncpu = demand_ncpu # Set to non-zero for fixed #CPUs.
        self.allocated_ncpu = 0
        self.new_cpus = []
        self.last_start_proc_time = 0.0

    def __iadd__(self, newproc):
        "add a processor to this coordinator's list"
        self.processors[newproc] = time.time()
        return self

    def __isub__(self, oldproc):
        "remove a processor from this coordinator's list"
        del self.processors[oldproc]
        return self

    def update_load(self):
        """tell this coordinator to use only allocated_ncpu processors,
        and to launch processors on the list of new_cpus.
        Simply spawns a thread to do this without danger of deadlock"""
        import threading
        t = threading.Thread(target=self.update_load_thread,
                           args=(self.allocated_ncpu, self.new_cpus))
        self.new_cpus = [] # DISCONNECT FROM OLD LIST TO PREVENT OVERWRITING
        t.start()

    def update_load_thread(self, ncpu, new_cpus):
        """tell this coordinator to use only ncpu processors,
        and to launch processors on the list of new_cpus.
        Run this in a separate thread to prevent deadlock."""
        self.server.set_max_clients(ncpu)
        if len(new_cpus) > 0 and \
           time.time() - self.last_start_proc_time > self.min_startup_time:
            self.server.start_processors(new_cpus) # SEND OUR LIST
            self.last_start_proc_time = time.time()


class HostInfo(ObjectFromString):
    _attrtype = {'maxload': float}


class XMLRPCServerBase(object):
    'Base class for creating an XMLRPC server for multiple objects'
    xmlrpc_methods = {'methodCall': 0, 'objectList': 0, 'objectInfo': 0}
    max_tb = 10
    _dispatch = safe_dispatch # RESTRICT XMLRPC TO JUST THE METHODS LISTED HERE

    def __init__(self, name, host='', port=5000, logRequests=False,
                 server=None):
        self.host = host
        self.name = name
        if server is not None:
            self.server = server
            self.port = port
        else:
            self.server, self.port = get_server(host, port, logRequests)
        self.server.register_instance(self)
        self.objDict = {}

    def __setitem__(self, name, obj):
        'add a new object to serve'
        self.objDict[name] = obj

    def __delitem__(self, name):
        del self.objDict[name]

    def objectList(self):
        'get list of named objects in this server: [(name,methodDict),...]'
        return [(name, obj.xmlrpc_methods) for (name, obj) in
                self.objDict.items()]

    def objectInfo(self, objname):
        'get dict of methodnames on the named object'
        try:
            return self.objDict[objname].xmlrpc_methods
        except KeyError:
            return 'error: server has no object named %s' % objname

    def methodCall(self, objname, methodname, args):
        'run the named method on the named object and return its result'
        try:
            obj = self.objDict[objname]
            if methodname in obj.xmlrpc_methods:
                m = getattr(obj, methodname)
            else:
                print >>sys.stderr, \
                      "methodCall: blocked unregistered method %s" % methodname
                return ''
        except (KeyError, AttributeError):
            return '' # RETURN FAILURE CODE
        return m(*args) # RUN THE OBJECT METHOD

    def serve_forever(self, demonize=None, daemonize=False):
        'launch the XMLRPC service.  if daemonize=True, detach & exit.'
        if demonize is not None:
            logging.warning("demonize is a deprecated argument to \
                            serve_forever; use 'daemonize' instead!")
            daemonize = demonize

        print 'Serving on interface "%s", port %d' % (self.host, self.port, )

        if daemonize:
            print "detaching to run as a daemon."
            pid = detach_as_demon_process(self)
            if pid:
                print 'PID', pid
                sys.exit(0)

        serve_forever(self)

    def serve_in_thread(self):
        thread.start_new_thread(serve_forever, (self, ))

    def register(self, url=None, name='index', server=None):
        'register our server with the designated index server'
        data=self.registrationData # RAISE ERROR IF NO DATA TO REGISTER...
        if server is None and url is not None:
            # Use the URL to get the index server.
            server = get_connection(url, name)
        if server is not None:
            server.registerServer('%s:%d' % (self.host, self.port), data)
        else: # DEFAULT: SEARCH WORLDBASEPATH TO FIND INDEX SERVER
            from pygr import worldbase
            worldbase._mdb.registerServer('%s:%d' % (self.host, self.port),
                                          data)


class ResourceController(object):
    """Centralized controller for getting resources and rules for
    making them.
    """
    xmlrpc_methods = {'load_balance': 0, 'setrule': 0, 'delrule': 0,
                      'report_load': 0, 'register_coordinator': 0,
                      'unregister_coordinator': 0, 'register_processor': 0,
                      'unregister_processor': 0, 'get_resource': 0,
                      'acquire_rule': 0, 'release_rule': 0, 'request_cpus': 0,
                      'retry_unused_hosts': 0, 'get_status': 0,
                      'setthrottle': 0, 'del_lock': 0, 'get_hostinfo': 0,
                      'set_hostinfo': 0}
    _dispatch = safe_dispatch # RESTRICT XMLRPC TO JUST THE METHODS LISTED HERE
    max_tb = 10

    def __init__(self, rc='controller', port=5000, overload_margin=0.6,
                 rebalance_frequency=1200, errlog=False, throttle=1.0):
        self.name = rc
        self.overload_margin = overload_margin
        self.rebalance_frequency = rebalance_frequency
        self.errlog = errlog
        self.throttle = throttle
        self.rebalance_time = time.time()
        self.must_rebalance = False
        self.host = get_hostname()
        self.hosts = FileDict(self.name + '.hosts', HostInfo)
        self.getrules()
        self.getresources()
        self.server, self.port = get_server(self.host, port)
        self.server.register_instance(self)
        self.coordinators = {}
        self.njob = 0
        self.locks = {}
        self.systemLoad = {}
        hostlist=[host for host in self.hosts]
        for host in hostlist: # 1ST ASSUME HOST EMPTY, THEN GET LOAD REPORTS
            hostFQDN = get_hostname(host) # CONVERT ALL HOSTNAMES TO FQDNs
            if hostFQDN != host: # USE FQDN FOR ALL SUBSEQUENT REFS!
                self.hosts[hostFQDN] = self.hosts[host]
                del self.hosts[host]
            self.systemLoad[hostFQDN] = 0.0

    __call__ = serve_forever

    def assign_load(self):
        "calculate the latest balanced loads"
        maxload = 0.
        total = 0.
        current_job = 99999999
        for c in self.coordinators.values():
            if c.priority > 0.0 and c.job_id < current_job:
                current_job = c.job_id # FIND 1ST NON-ZER0 PRIORITY JOB
        for c in self.coordinators.values():
            if c.demand_ncpu: # DEMANDS A FIXED #CPUS, NO LOAD BALANCING
                c.run = True
            elif c.job_id == current_job or c.immediate:
                c.run = True # YES, RUN THIS JOB
                total += c.priority
            else:
                c.run=False
        for v in self.hosts.values(): # SUM UP TOTAL CPUS
            maxload += v.maxload
        maxload *= self.throttle # APPLY OUR THROTTLE CONTROL
        for c in self.coordinators.values(): #REMOVE DEMANDED CPUS
            if c.demand_ncpu:
                maxload -= c.demand_ncpu
        if maxload < 0.: # DON'T ALLOW NEGATIVE VALUES
            maxload = 0.
        if total > 0.: # DON'T DIVIDE BY ZERO...
            maxload /= float(total)
        for c in self.coordinators.values(): # ALLOCATE SHARE OF TOTAL CPUS...
            if c.demand_ncpu: # ALLOCATE EXACTLY THE NUMBER REQUESTED
                c.allocated_ncpu = int(c.demand_ncpu)
            elif c.run: # COMPUTE BASED ON PRIORITY SHARE
                c.allocated_ncpu = int(maxload * c.priority)
            else: # NOT RUNNING
                c.allocated_ncpu = 0
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def assign_processors(self):
        "hand out available processors to coordinators in order of need"
        margin = self.overload_margin - 1.0
        free_cpus = []
        nproc = {}
        for c in self.coordinators.values(): # COUNT NUMBER OF PROCS
            for host, pid in c.processors: # RUNNING ON EACH HOST
                try:
                    nproc[host] += 1.0 # INCREMENT AN EXISTING COUNT
                except KeyError:
                    nproc[host] = 1.0 # NEW, SO SET INITIAL COUNT
        for host in self.hosts: # BUILD LIST OF HOST CPUS TO BE ASSIGNED
            if host not in self.systemLoad: # ADDING A NEW HOST
                self.systemLoad[host] = 0.0 # DEFAULT LOAD: ASSUME HOST EMPTY
            try: # host MAY NOT BE IN nproc, SO CATCH THAT ERROR
                if self.systemLoad[host] > nproc[host]:
                    raise KeyError # USE self.systemLoad[host]
            except KeyError:
                load = self.systemLoad[host] # MAXIMUM VALUE
            else:
                load = nproc[host] # MAXIMUM VALUE
            if load < self.hosts[host].maxload + margin:
                free_cpus += int(self.hosts[host].maxload
                                 + self.overload_margin - load) * [host]
        if len(free_cpus) == 0: # WE DON'T HAVE ANY CPUS TO GIVE OUT
            return False
        l = [] # BUILD A LIST OF HOW MANY CPUS EACH COORDINATOR NEEDS
        for c in self.coordinators.values():
            ncpu = c.allocated_ncpu - len(c.processors)
            if ncpu > 0:
                l += ncpu*[c]  # ADD c TO l EXACTLY ncpu TIMES
        import random
        random.shuffle(l) # REORDER LIST OF COORDINATORS RANDOMLY
        i = 0 # INDEX INTO OUR l LIST
        while i < len(free_cpus) and i < len(l):
            # Hand out free CPUs one by one.
            l[i].new_cpus.append(free_cpus[i])
            i += 1
        return i > 0 # RETURN TRUE IF WE HANDED OUT SOME PROCESSORS

    def load_balance(self):
        "recalculate load assignments, and assign free cpus"
        self.rebalance_time = time.time() # RESET OUR FLAGS
        self.must_rebalance = False
        # Calculate how many CPUs each coordinator should get.
        self.assign_load()
        # Assign free CPUs to coordinators which need them.
        self.assign_processors()
        for c in self.coordinators.values():
            c.update_load() # INFORM THE COORDINATOR
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def get_hostinfo(self, host, attr):
        "get a host attribute"
        return getattr(self.hosts[host], attr)

    def set_hostinfo(self, host, attr, val):
        "increase or decrease the maximum load allowed on a given host"
        try:
            setattr(self.hosts[host], attr, val)
        except KeyError:
            self.hosts[host] = HostInfo('%s=%s' % (attr, str(val)))
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def getrules(self):
        import shelve
        self.rules = dbfile.shelve_open(self.name + '.rules')

    def getresources(self):
        import shelve
        self.resources = dbfile.shelve_open(self.name + '.rsrc')

    def setrule(self, rsrc, rule):
        "save a resource generation rule into our database"
        self.rules[rsrc] = rule
        self.rules.close() # THIS IS THE ONLY WAY I KNOW TO FLUSH...
        self.getrules()
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def delrule(self, rsrc):
        "delete a resource generation rule from our database"
        try:
            del self.rules[rsrc]
        except KeyError:
            print >>sys.stderr, "Attempt to delete unknown resource rule %s" \
                    % rsrc
        else:
            self.rules.close() # THIS IS THE ONLY WAY I KNOW TO FLUSH...
            self.getrules()
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def setthrottle(self, throttle):
        "set the total level of usage of available CPUs, usually 1.0"
        self.throttle = float(throttle)
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def report_load(self, host, pid, load):
        "save a reported load from one of our processors"
        self.systemLoad[host] = load
        # AT A REGULAR INTERVAL WE SHOULD REBALANCE LOAD
        if self.must_rebalance or \
               time.time() - self.rebalance_time > self.rebalance_frequency:
            self.load_balance()
        if load < self.hosts[host].maxload + self.overload_margin:
            return True  # OK TO CONTINUE
        else:
            return False # THIS SYSTEM OVERLOADED, TELL PROCESSOR TO EXIT

    def register_coordinator(self, name, url, user, priority, resources,
                             immediate, demand_ncpu):
        "save a coordinator's registration info"
        try:
            print >>sys.stderr, 'change_priority: %s (%s,%s): %f -> %f' \
                  % (name, user, url, self.coordinators[url].priority,
                     priority)
            self.coordinators[url].priority = priority
            self.coordinators[url].immediate = immediate
            self.coordinators[url].demand_ncpu = demand_ncpu
        except KeyError:
            print >>sys.stderr, 'register_coordinator: %s (%s,%s): %f' \
                  % (name, user, url, priority)
            self.coordinators[url] = CoordinatorInfo(name, url, user, priority,
                                                     resources, self.njob,
                                                     immediate, demand_ncpu)
            self.njob += 1 # INCREMENT COUNT OF JOBS WE'VE REGISTERED
        self.must_rebalance = True # FORCE REBALANCING ON NEXT OPPORTUNITY
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def unregister_coordinator(self, name, url, message):
        "remove a coordinator from our list"
        try:
            del self.coordinators[url]
            print >>sys.stderr, 'unregister_coordinator: %s (%s): %s' \
                  % (name, url, message)
            self.load_balance() # FORCE IT TO REBALANCE THE LOAD TO NEW JOBS...
        except KeyError:
            print >>sys.stderr, 'unregister_coordinator: %s unknown:%s (%s)' \
                  % (name, url, message)
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def request_cpus(self, name, url):
        "return a list of hosts for this coordinator to run processors on"
        try:
            c = self.coordinators[url]
        except KeyError:
            print >>sys.stderr, 'request_cpus: unknown coordinator %s @ %s' \
                    % (name, url)
            return [] # HAND BACK AN EMPTY LIST
        # Calculate how many CPUs each coordinator should get.
        self.assign_load()
        # Assign free CPUs to coordinators which need them.
        self.assign_processors()
        new_cpus=tuple(c.new_cpus) # MAKE A NEW COPY OF THE LIST OF HOSTS
        del c.new_cpus[:] # EMPTY OUR LIST
        return new_cpus

    def register_processor(self, host, pid, url):
        "record a new processor starting up"
        try:
            self.coordinators[url] += (host, pid)
            self.systemLoad[host] += 1.0 # THIS PROBABLY INCREASES LOAD BY 1
        except KeyError:
            pass
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def unregister_processor(self, host, pid, url):
        "processor shutting down, so remove it from the list"
        try:
            self.coordinators[url] -= (host, pid)
            self.systemLoad[host] -= 1.0 # THIS PROBABLY DECREASES LOAD BY 1
            if self.systemLoad[host] < 0.0:
                self.systemLoad[host] = 0.0
            for k, v in self.locks.items(): # MAKE SURE THIS PROC HAS NO LOCKS
                h = k.split(':')[0]
                if h == host and v == pid:
                    del self.locks[k] # REMOVE ALL ITS PENDING LOCKS
        except KeyError:
            pass
        self.load_balance() # FREEING A PROCESSOR, SO REBALANCE TO USE THIS
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def get_resource(self, host, pid, rsrc):
        """return a filename for the resource, or False if rule must be
        applied, or True if client must wait to get the resource"""
        key = host + ':' + rsrc
        try: # JUST HAND BACK THE RESOURCE
            return self.resources[key]
        except KeyError:
            if key in self.locks:
                return True # TELL CLIENT TO WAIT
            else:
                return False # TELL CLIENT TO ACQUIRE IT VIA RULE

    def acquire_rule(self, host, pid, rsrc):
        """lock the resource on this specific host
        and return its production rule"""
        if rsrc not in self.rules:
            return False # TELL CLIENT NO SUCH RULE
        key = host + ':' + rsrc
        if key in self.locks:
            return True # TELL CLIENT TO WAIT
        # Lock this resource on this host until constructed.
        self.locks[key] = pid
        return self.rules[rsrc] # RETURN THE CONSTRUCTION RULE

    def release_rule(self, host, pid, rsrc):
        """client is done applying this rule, it is now safe
        to give out the resource"""
        key = host + ':' + rsrc
        self.del_lock(host, rsrc)
        # Add the file name to resource list.
        self.resources[key] = self.rules[rsrc][0]
        self.resources.close() # THIS IS THE ONLY WAY I KNOW TO FLUSH THIS...
        self.getresources()
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def del_lock(self, host, rsrc):
        "delete a lock on a pending resource construction process"
        key = host + ':' + rsrc
        try:
            del self.locks[key] # REMOVE THE LOCK
        except KeyError:
            print >> sys.stderr, "attempt to release non-existent lock \
                    %s,%s:%d" % (host, rule, pid)
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def retry_unused_hosts(self):
        "reset systemLoad for hosts that have no jobs running"
        myhosts = {}
        for c in self.coordinators.values(): # LIST HOSTS WE'RE CURRENTLY USING
            for host, pid in c.processors:
                myhosts[host] = None # MARK THIS HOST AS IN USE
        for host in self.systemLoad: # RESET LOAD FOR ALL HOSTS WE'RE NOT USING
            if host not in myhosts:
                self.systemLoad[host] = 0.0
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def get_status(self):
        """get report of system loads, max loads, coordinators, rules,
        resources, locks"""
        l = [(name, host.maxload) for name, host in self.hosts.items()]
        l.sort()
        return self.name, self.errlog, self.systemLoad, l, \
               [(c.name, c.url, c.priority, c.allocated_ncpu,
                 len(c.processors), c.start_time) for c in
                self.coordinators.values()], dict(self.rules), \
                dict(self.resources), self.locks


class AttrProxy(object):

    def __init__(self, getattr_proxy, k):
        self.getattr_proxy = getattr_proxy
        self.k = k

    def __getattr__(self, attr):
        try:
            val = self.getattr_proxy(self.k, attr) # GET IT FROM OUR PROXY
        except:
            raise AttributeError('unable to get proxy attr ' + attr)
        setattr(self, attr, val) # CACHE THIS ATTRIBUTE RIGHT HERE!
        return val


class DictAttrProxy(dict):

    def __init__(self, getattr_proxy):
        dict.__init__(self)
        self.getattr_proxy = getattr_proxy

    def __getitem__(self, k):
        try:
            return dict.__getitem__(self, k)
        except KeyError:
            val = AttrProxy(self.getattr_proxy, k)
            self[k] = val
            return val


class Coordinator(object):
    """Run our script as Processor on one or more client nodes, using
    XMLRPC communication between clients and server.
    On the server all output is logged to name.log,
    and successfully completed task IDs are stored in name.success,
    and error task IDs are stored in name.error
    On the clients all output is logged to the file name_#.log in the user's
    and/or system-specific temporary directory."""
    xmlrpc_methods = {'start_processors': 0, 'register_client': 0,
                      'unregister_client': 0, 'report_success': 0,
                      'report_error': 0, 'next': 0, 'get_status': 0,
                      'set_max_clients': 0, 'stop_client': 0}
    _dispatch = safe_dispatch # RESTRICT XMLRPC TO JUST THE METHODS LISTED HERE
    max_tb = 10 # MAXIMUM #STACK LEVELS TO PRINT IN TRACEBACKS
    max_ssh_errors = 5 #MAXIMUM #ERRORS TO PERMIT IN A ROW BEFORE QUITTING
    python = 'python' # DEFAULT EXECUTABLE FOR RUNNING OUR CLIENTS

    def __init__(self, name, script, it, resources, port=8888, priority=1.0,
                 rc_url=None, errlog=False, immediate=False,
                 ncpu_limit=999999, demand_ncpu=0, max_initialization_errors=3,
                 **kwargs):
        self.name = name
        self.script = script
        self.it = iter(it) # Make sure self.it is an iterator.
        self.resources = resources
        self.priority = priority
        self.errlog = errlog
        self.immediate = immediate
        self.ncpu_limit = ncpu_limit
        self.demand_ncpu = demand_ncpu
        self.max_initialization_errors = max_initialization_errors
        self.kwargs = kwargs
        self.host = get_hostname()
        self.user = os.environ['USER']
        try:
            # Make sure ssh-agent is available before we launch
            # a lot of processes.
            a = os.environ['SSH_AGENT_PID']
        except KeyError:
            raise OSError(1, 'SSH_AGENT_PID not found. No ssh-agent running?')
        self.dir = os.getcwd()
        self.n = 0
        self.nsuccess = 0
        self.nerrors = 0
        self.nssh_errors = 0
        self.iclient = 0
        self.max_clients = 40
        if rc_url is None:
            # Try the default resource-controller address on the same host.
            rc_url = 'http://%s:5000' % self.host
        self.rc_url = rc_url
        # Connect to the resource controller...
        self.rc_server = xmlrpclib.ServerProxy(rc_url)
        # ...create an XMLRPC server.
        self.server, self.port = get_server(self.host, port)
        # ...and provide it with all the methods.
        self.server.register_instance(self)
        self.clients = {}
        self.pending = {}
        self.already_done = {}
        self.stop_clients = {}
        self.logfile = {}
        self.clients_starting = {}
        self.clients_initializing = {}
        self.initialization_errors = {}
        try: # LOAD LIST OF IDs ALREADY SUCCESSFULLY PROCESSED, IF ANY
            f = file(name + '.success', 'rU') # text file
            for line in f:
                self.already_done[line.strip()] = None
            f.close()
        except IOError: # OK IF NO SUCCESS FILE YET, WE'LL CREATE ONE.
            pass
        # Success file is to be cumulative but overwrite the error file.
        self.successfile = file(name + '.success', 'a')
        self.errorfile = file(name + '.error', 'w')
        self.done = False
        self.hosts = DictAttrProxy(self.rc_server.get_hostinfo)
        self.register()

    def __call__(self, *l, **kwargs):
        "start the server, and launch a cpu request in a separate thread"
        import threading
        t = threading.Thread(target=self.initialize_thread)
        t.start()
        serve_forever(self, *l, **kwargs)

    def initialize_thread(self):
        """run this method in a separate thread
        to bootstrap our initial cpu request"""
        time.sleep(5) # GIVE serve_forever() TIME TO START SERVER
        # Now ask the controller to rebalance and give up CPUs.
        self.rc_server.load_balance()

    def start_client(self, host):
        "start a processor on a client node"
        import tempfile
        if len(self.clients) >= self.ncpu_limit:
            print >>sys.stderr, 'start_client: blocked, CPU limit', \
                  len(self.clients), self.ncpu_limit
            return # DON'T START ANOTHER PROCESS, TOO MANY ALREADY
        if len(self.clients) >= self.max_clients:
            print >>sys.stderr, 'start_client: blocked, too many already', \
                  len(self.clients), self.max_clients
            return # DON'T START ANOTHER PROCESS, TOO MANY ALREADY
        try:
            if len(self.clients_starting[host]) >= self.max_ssh_errors:
                print >>sys.stderr, \
                      'start_client: blocked, too many unstarted jobs:', \
                      host, self.clients_starting[host]
                return # DON'T START ANOTHER PROCESS, host MAY BE DEAD...
        except KeyError: # NO clients_starting ON host, GOOD!
            pass
        try:
            if len(self.initialization_errors[host]) >= \
               self.max_initialization_errors:
                print >>sys.stderr, 'start_client: blocked, too many \
                        initialization errors:', host, \
                        self.initialization_errors[host]
                return # DON'T START ANOTHER PROCESS, host HAS A PROBLEM
        except KeyError: # NO initialization_errors ON host, GOOD!
            pass
        try:
            sshopts = self.hosts[host].sshopts # GET sshopts VIA XMLRPC
        except AttributeError:
            sshopts = ''
        logfile = os.path.join(tempfile.gettempdir(), '%s_%d.log' \
                               % (self.name, self.iclient))
        # PASS OUR KWARGS ON TO THE CLIENT PROCESSOR
        kwargs = ' '.join(['--%s=%s' % (k, v) for k, v in self.kwargs.items()])
        cmd = 'cd %s;%s %s --url=http://%s:%d --rc_url=%s --logfile=%s %s %s' \
             % (self.dir, self.python, self.script, self.host, self.port,
                self.rc_url, logfile, self.name, kwargs)
        # UGH, HAVE TO MIX CSH REDIRECTION (REMOTE) WITH SH REDIRECTION (LOCAL)
        ssh_cmd = "ssh %s %s '(%s) </dev/null >&%s &' </dev/null >>%s 2>&1 &" \
                 % (sshopts, host, cmd, logfile, self.errlog)
        print >>sys.stderr, 'SSH: ' + ssh_cmd
        self.logfile[logfile] = [host, False, self.iclient] # NO PID YET
        try: # RECORD THIS CLIENT AS STARTING UP
            self.clients_starting[host][self.iclient] = time.time()
        except KeyError: # CREATE A NEW HOST ENTRY
            self.clients_starting[host] = {self.iclient: time.time()}
        # RUN SSH IN BACKGROUND TO AVOID WAITING FOR IT TO TIMEOUT!!!
        os.system(ssh_cmd) # LAUNCH THE SSH PROCESS, SHOULD RETURN IMMEDIATELY
        self.iclient += 1 # ADVANCE OUR CLIENT COUNTER

    def start_processors(self, hosts):
        "start processors on the list of hosts using SSH transport"
        for host in hosts: # LAUNCH OURSELVES AS PROCESSOR ON ALL THESE HOSTS
            self.start_client(host)
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def register(self):
        "register our existence with the resource controller"
        url = 'http://%s:%d' % (self.host, self.port)
        self.rc_server.register_coordinator(self.name, url, self.user,
                                            self.priority, self.resources,
                                            self.immediate, self.demand_ncpu)

    def unregister(self, message):
        "tell the resource controller we're exiting"
        url = 'http://%s:%d' % (self.host, self.port)
        self.rc_server.unregister_coordinator(self.name, url, message)

    def register_client(self, host, pid, logfile):
        'XMLRPC call to register client hostname and PID as starting_up'
        print >>sys.stderr, 'register_client: %s:%d' % (host, pid)
        self.clients[(host, pid)] = 0
        try:
            self.logfile[logfile][1] = pid # SAVE OUR PID
            iclient = self.logfile[logfile][2] # GET ITS CLIENT ID
            del self.clients_starting[host][iclient] #REMOVE FROM STARTUP LIST
        except KeyError:
            print >>sys.stderr, 'no client logfile?', host, pid, logfile
        self.clients_initializing[(host, pid)] = logfile
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def unregister_client(self, host, pid, message):
        'XMLRPC call to remove client from register as exiting'
        print >>sys.stderr, 'unregister_client: %s:%d %s' \
                % (host, pid, message)
        try:
            del self.clients[(host, pid)]
        except KeyError:
            print >>sys.stderr, 'unregister_client: unknown client %s:%d' \
                    % (host, pid)
        try: # REMOVE IT FROM THE LIST OF CLIENTS TO SHUTDOWN, IF PRESENT
            del self.stop_clients[(host, pid)]
        except KeyError:
            pass
        try: # REMOVE FROM INITIALIZATION LIST
            del self.clients_initializing[(host, pid)]
        except KeyError:
            pass
        if len(self.clients) == 0 and self.done:
            # No more tasks or clients, the server can exit.
            self.exit("Done")
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def report_success(self, host, pid, success_id):
        'mark task as successfully completed'
        # Keep permanent record of success ID.
        print >>self.successfile, success_id
        self.successfile.flush()
        self.nsuccess += 1
        try:
            self.clients[(host, pid)] += 1
        except KeyError:
            print >>sys.stderr, 'report_success: unknown client %s:%d' \
                    % (host, pid)
        try:
            del self.pending[success_id]
        except KeyError:
            print >>sys.stderr, 'report_success: unknown ID %s' \
                    % str(success_id)
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def report_error(self, host, pid, id, tb_report):
        "get traceback report from client as text"
        print >>sys.stderr, "TRACEBACK: %s:%s ID %s\n%s" % \
              (host, str(pid), str(id), tb_report)
        if (host, pid) in self.clients_initializing:
            logfile = self.clients_initializing[(host, pid)]
            try:
                self.initialization_errors[host].append(logfile)
            except KeyError:
                self.initialization_errors[host] = [logfile]
        try:
            del self.pending[id]
        except KeyError:
            # Not associated with an actual task ID, do not record.
            if id is not None and id is not False:
                print >>sys.stderr, 'report_error: unknown ID %s' % str(id)
        else:
            print >>self.errorfile, id # KEEP PERMANENT RECORD OF FAILURE ID
            self.nerrors += 1
            self.errorfile.flush()
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def next(self, host, pid, success_id):
        'return next ID from iterator to the XMLRPC caller'
        if (host, pid) not in self.clients:
            print >>sys.stderr, 'next: unknown client %s:%d' % (host, pid)
            return False # HAND BACK "NO MORE FOR YOU TO DO" SIGNAL
        try: # INITIALIZATION DONE, SO REMOVE FROM INITIALIZATION LIST
            del self.clients_initializing[(host, pid)]
        except KeyError:
            pass
        if success_id is not False:
            self.report_success(host, pid, success_id)
        if self.done: # EXHAUSTED OUR ITERATOR, SO SHUT DOWN THIS CLIENT
            return False # HAND BACK "NO MORE FOR YOU TO DO" SIGNAL
        try:  # CHECK LIST FOR COMMAND TO SHUT DOWN THIS CLIENT
            del self.stop_clients[(host, pid)] # IS IT IN stop_clients?
            return False # IF SO, HAND BACK "NO MORE FOR YOU TO DO" SIGNAL
        except KeyError: # DO ONE MORE CHECK: ARE WE OVER OUR MAX ALLOWED LOAD?
            if len(self.clients) > self.max_clients:
                # Yes, better throttle down.
                print >>sys.stderr, 'next: halting %s:too many processors \
                        (%d>%d)' % (host, len(self.clients), self.max_clients)
                return False # HAND BACK "NO MORE FOR YOU TO DO" SIGNAL
        for id in self.it: # GET AN ID WE CAN USE
            if str(id) not in self.already_done:
                self.n += 1 # GREAT, WE CAN USE THIS ID
                self.lastID = id
                self.pending[id] = (host, pid, time.time())
                print >>sys.stderr, 'giving id %s to %s:%d' % (str(id),
                                                               host, pid)
                return id
        print >>sys.stderr, 'exhausted all items from iterator!'
        self.done = True # EXHAUSTED OUR ITERATOR
        # Release our claims on any further processor allication
        # and inform the resource controller about it.
        self.priority = 0.0
        self.register()
        return False # False IS CONFORMABLE BY XMLRPC...

    def get_status(self):
        "return basic status info on number of jobs finished, client list etc."
        client_report = [client + (nsuccess, ) for client, nsuccess
                         in self.clients.items()]
        pending_report = [(k, ) + v for k, v in self.pending.items()]
        return self.name, self.errlog, self.n, self.nsuccess, self.nerrors, \
                client_report, pending_report, self.logfile

    def set_max_clients(self, n):
        "change the maximum number of clients we should have running"
        self.max_clients = int(n)  # MAKE SURE n IS CONVERTABLE TO int
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def stop_client(self, host, pid):
        "set signal forcing this client to exit on next iteration"
        self.stop_clients[(host, pid)] = None
        return True  # USE THIS AS DEFAULT XMLRPC RETURN VALUE

    def exit(self, message):
        "clean up and close this server"
        self.unregister(message)
        self.successfile.close()
        self.errorfile.close()
        sys.exit()


try:

    class ResourceFile(file):
        """wrapper around some locking behavior, to ensure only one
        copy operation performed for a given resource on a given host.
        Otherwise, it's just a regular file object."""

        def __init__(self, resource, rule, mode, processor):
            "resource is name of the resource; rule is (localFile, cpCommand)"
            self.resource = resource
            self.processor = processor
            localFile, cpCommand = rule
            if not os.access(localFile, os.R_OK):
                cmd = cpCommand % localFile
                print 'copying data:', cmd
                os.system(cmd)
            # Now, initialise as a real file object.
            file.__init__(self, localFile, mode)

        def close(self):
            # Release the lock we placed on this rule.
            self.processor.release_rule(self.resource)
            file.close(self)
except TypeError:
    pass


class Processor(object):
    'provides an iterator interface to an XMLRPC ID server'
    max_errors_in_a_row = 10 # LOOKS LIKE NOTHING WORKS HERE, SO QUIT!
    max_tb = 10 # DON'T SHOW MORE THAN 10 STACK LEVELS FOR A TRACEBACK
    report_frequency = 600
    overload_max = 5 # Max number of overload events in a row before we exit.

    def __init__(self, url = "http://localhost:8888",
                 rc_url = 'http://localhost:5000', logfile=False, **kwargs):
        self.url = url
        self.logfile = logfile
        self.server = xmlrpclib.ServerProxy(url)
        self.rc_url = rc_url
        self.rc_server = xmlrpclib.ServerProxy(rc_url)
        self.host = get_hostname()
        self.pid = os.getpid()
        self.user = os.environ['USER']
        self.success_id = False
        self.pending_id = False
        self.exit_message = 'MYSTERY-EXIT please debug'
        self.overload_count = 0

    def register(self):
        "add ourselves to list of processors for this server"
        self.server.register_client(self.host, self.pid, self.logfile)
        self.rc_server.register_processor(self.host, self.pid, self.url)
        print >>sys.stderr, 'REGISTERED:', self.url, self.rc_url

    def unregister(self, message):
        "remove ourselves from list of processors for this server"
        if self.success_id is not False: # REPORT THAT LAST JOB SUCCEEDED!
            self.report_success(self.success_id)
        self.server.unregister_client(self.host, self.pid, message)
        self.rc_server.unregister_processor(self.host, self.pid, self.url)
        print >>sys.stderr, 'UNREGISTERED:', self.url, self.rc_url, message

    def __iter__(self):
        return self

    def next(self):
        "get next ID from server"
        # REPORT LAST JOB SUCCESSFULLY COMPLETED, IF ANY
        while 1:
            id = self.server.next(self.host, self.pid, self.success_id)
            self.success_id = False # ERASE SUCCESS ID
            if id is True: # WE'RE BEING TOLD TO JUST WAIT
                time.sleep(60) # SO GO TO SLEEP FOR A MINUTE
            else:
                break
        if id is False: # NO MODE id FOR US TO PROCESS, SO QUIT
            self.serverStopIteration = True # RECORD THIS AS GENUINE END EVENT
            raise StopIteration
        else: # HAND BACK THE id TO THE USER
            self.pending_id = id
            return id

    def report_success(self, id):
        "report successful completion of task ID"
        self.server.report_success(self.host, self.pid, id)

    def report_error(self, id):
        "report an error using traceback.print_exc()"
        import StringIO
        err_report = StringIO.StringIO()
        traceback.print_exc(self.max_tb, sys.stderr) #REPORT TB TO OUR LOG
        traceback.print_exc(self.max_tb, err_report) #REPORT TB TO SERVER
        self.server.report_error(self.host, self.pid, id,
                                 err_report.getvalue())
        err_report.close()

    def report_load(self):
        "report system load"
        load = os.getloadavg()[0] # GET 1 MINUTE LOAD AVERAGE
        if self.rc_server.report_load(self.host, self.pid, load) is False:
            # Are we consistently overloaded for an extended time period?
            self.overload_count += 1
            if self.overload_count > self.overload_max:
                # Limit exceeded, exit.
                self.exit('load too high')
        else:
            self.overload_count = 0

    def open_resource(self, resource, mode):
        "get a file object for the requested resource, opened in mode"
        while 1:
            rule = self.rc_server.get_resource(self.host, self.pid, resource)
            if rule is False: # WE HAVE TO LOCK AND APPLY A RULE...
                rule = self.acquire_rule(resource)
                if rule is True:
                    # Looks like a race condition, wait a minute before
                    # trying again.
                    time.sleep(60)
                    continue
                # Construct the resource.
                return ResourceFile(resource, rule, mode, self)
            elif rule is True:
                # Rule is locked by another processor, wait a minute before
                # trying again.
                time.sleep(60)
            else: # GOT A REGULAR FILE, SO JUST OPEN IT
                return file(rule, mode)

    def acquire_rule(self, resource):
        """lock the specified resource rule for this host
        so that it's safe to build it"""
        rule = self.rc_server.acquire_rule(self.host, self.pid, resource)
        if rule is False: # NO SUCH RESOURCE?!?
            self.exit('invalid resource: ' + resource)
        return rule

    def release_rule(self, resource):
        "release our lock on this resource rule, so others can use it"
        self.rc_server.release_rule(self.host, self.pid, resource)

    def exit(self, message):
        "save message for self.unregister() and force exit"
        self.exit_message = message
        raise SystemExit

    def run_all(self, resultGenerator, **kwargs):
        "run until all task IDs completed, trap & report all errors"
        errors_in_a_row = 0
        it = resultGenerator(self, **kwargs) # GET ITERATOR FROM GENERATOR
        report_time = time.time()
        self.register() # REGISTER WITH RESOURCE CONTROLLER & COORDINATOR
        initializationError = None
        try: # TRAP ERRORS BOTH IN USER CODE AND coordinator CODE
            while 1:
                try: # TRAP AND REPORT ALL ERRORS IN USER CODE
                    id = it.next() # THIS RUNS USER CODE FOR ONE ITERATION
                    self.success_id = id  # MARK THIS AS A SUCCESS...
                    errors_in_a_row = 0
                    initializationError = False
                except StopIteration: # NO MORE TASKS FOR US...
                    if not hasattr(self, 'serverStopIteration'): # Weird!
                        # USER CODE RAISED StopIteration?!?
                        self.report_error(self.pending_id) # REPORT THE PROBLEM
                        self.exit_message = 'user StopIteration error'
                    elif initializationError:
                        self.exit_message = 'initialization error'
                    else:
                        self.exit_message = 'done'
                    break
                except SystemExit: # sys.exit() CALLED
                    raise  # WE REALLY DO WANT TO EXIT.
                except: # MUST HAVE BEEN AN ERROR IN THE USER CODE
                    if initializationError is None: # STILL IN INITIALIZATION
                        initializationError=True
                    self.report_error(self.pending_id) # REPORT THE PROBLEM
                    errors_in_a_row +=1
                    if errors_in_a_row>=self.max_errors_in_a_row:
                        self.exit_message='too many errors'
                        break
                if time.time()-report_time>self.report_frequency:
                    self.report_load() # SEND A ROUTINE LOAD REPORT
                    report_time=time.time()
        except SystemExit: # sys.exit() CALLED
            pass  # WE REALLY DO WANT TO EXIT.
        except: # IMPORTANT TO TRAP ALL ERRORS SO THAT WE UNREGISTER!!
            traceback.print_exc(self.max_tb, sys.stderr) #REPORT TB TO OUR LOG
            self.exit_message='error trap'
        self.unregister('run_all '+self.exit_message) # MUST UNREGISTER!!

    def run_interactive(self, it, n=1, **kwargs):
        "run n task IDs, with no error trapping"
        if not hasattr(it, 'next'):
            # Assume 'it' is a generator, use it to get an iterator.
            it = it(self, **kwargs)
        i=0
        self.register() # REGISTER WITH RESOURCE CONTROLLER & COORDINATOR
        try: # EVEN IF ERROR OCCURS, WE MUST UNREGISTER!!
            for id in it:
                self.success_id=id
                i+=1
                if i>=n:
                    break
        except:
            self.unregister('run_interactive error') # MUST UNREGISTER!!!
            raise # SHOW THE ERROR INTERACTIVELY
        self.unregister('run_interactive exit')
        return it # HAND BACK ITERATOR IN CASE USER WANTS TO RUN MORE...


def parse_argv():
    """parse sys.argv into a dictionary of GNU-style args (--foo=bar)
    and a list of other args"""
    d = {}
    l = []
    for v in sys.argv[1:]:
        if v[:2] == '--':
            try:
                k, v = v[2:].split('=')
                d[k] = v
            except ValueError:
                d[v[2:]] = None
        else:
            l.append(v)
    return d, l


def start_client_or_server(clientGenerator, serverGenerator, resources,
                           script):
    """start controller, client or server depending on whether
    we get coordinator argument from the command-line args.

    Client must be a generator function that takes Processor as argument,
    and uses it as an iterator.
    Also, clientGenerator must yield the IDs that the Processor provides
    (this structure allows us to trap all exceptions from clientGenerator,
    while allowing it to do resource initializations that would be
    much less elegant in a callback function.)

    Server must be a function that returns an iterator (e.g. a generator).
    Resources is a list of strings naming the resources we need
    copied to local host for client to be able to do its work.

    Both client and server constructors use **kwargs to get command
    line arguments (passed as GNU-style --foo=bar;
    see the constructor arguments to see the list of
    options that each can be passed.

    #CALL LIKE THIS FROM yourscript.py:
    import coordinator
    if __name__ == '__main__':
      coordinator.start_client_or_server(clientGen, serverGen,
        resources,__file__)

    To start the resource controller:
      python coordinator.py --rc=NAME [options]

    To start a job coordinator:
      python yourscript.py NAME [--rc_url=URL] [options]

    To start a job processor:
      python yourscript.py --url=URL --rc_url=URL [options]"""
    d, l = parse_argv()
    if 'url' in d: # WE ARE A CLIENT!
        client = Processor(**d)
        time.sleep(5) # GIVE THE SERVER SOME BREATHING SPACE
        client.run_all(clientGenerator, **d)
    elif 'rc' in d: # WE ARE THE RESOURCE CONTROLLER
        rc_server = ResourceController(**d) # NAME FOR THIS CONTROLLER...
        detach_as_demon_process(rc_server)
        rc_server() # START THE SERVER
    else: # WE ARE A SERVER
        try: # PASS OUR KWARGS TO THE SERVER FUNCTION
            it = serverGenerator(**d)
        except TypeError: # DOESN'T WANT ANY ARGS?
            it = serverGenerator()
        server = Coordinator(l[0], script, it, resources, **d)
        detach_as_demon_process(server)
        server() # START THE SERVER


class CoordinatorMonitor(object):
    "Monitor a Coordinator."

    def __init__(self, coordInfo):
        self.name, self.url, self.priority, self.allocated_ncpu, \
                self.ncpu, self.start_time = coordInfo
        self.server = xmlrpclib.ServerProxy(self.url)
        self.get_status()

    def get_status(self):
        self.name, self.errlog, self.n, self.nsuccess, self.nerrors, \
                self.client_report, self.pending_report, \
                self.logfile = self.server.get_status()
        print "Got status from Coordinator: ", self.name, self.url

    def __getattr__(self, attr):
        "just pass on method requests to our server"
        return getattr(self.server, attr)


class RCMonitor(object):
    """monitor a ResourceController.  Useful methods:
    get_status()
    load_balance()
    setrule(rsrc,rule)
    delrule(rsrc)
    setload(host,maxload)
    retry_unused_hosts()
    Documented in ResourceController docstrings."""

    def __init__(self, host=None, port=5000):
        host = get_hostname(host) # GET FQDN
        self.rc_url = 'http://%s:%d' % (host, port)
        self.rc_server = xmlrpclib.ServerProxy(self.rc_url)
        self.get_status()

    def get_status(self):
        self.name, self.errlog, self.systemLoad, self.hosts, \
                coordinators, self.rules, self.resources, \
                self.locks = self.rc_server.get_status()
        print "Got status from ResourceController:", self.name, self.rc_url
        self.coordinators = {}
        for cinfo in coordinators:
            try: # IF COORDINATOR HAS DIED, STILL WANT TO RETURN RCMonitor...
                self.coordinators[cinfo[0]] = CoordinatorMonitor(cinfo)
            except socket.error, e: # JUST COMPLAIN, BUT CONTINUE...
                print >>sys.stderr, "Unable to connect to coordinator:", \
                        cinfo, e

    def __getattr__(self, attr):
        "just pass on method requests to our rc_server"
        return getattr(self.rc_server, attr)


def test_client(server, **kwargs):
    for id in server:
        print 'ID', id
        yield id
        time.sleep(1)


def test_server():
    return range(1000)

if __name__ == '__main__':
    start_client_or_server(test_client, test_server, [], __file__)
