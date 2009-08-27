:mod:`coordinator` --- XMLRPC-based parallel cluster interface
==================================================

.. module:: coordinator
   :synopsis: XMLRPC-based parallel cluster interface.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>


This module provides a framework for running subtasks distributed over many computers, 
in a pythonic way, using SSH for secure process invocation and 
XMLRPC for message passing. Also provides simple interface for 
queuing and managing any number of such "batch jobs".

I will first describe some classes for simple XMLRPC services, then proceed
to the job control classes.

XMLRPCServerBase
----------------
Base class for creating an XMLRPC server to serve data from multiple objects.
On the server-side, this object can be treated as a dictionary whose
keys are object names, and whose associated values are the server
objects that will serve functionality to XMLRPC clients.
It provides an XMLRPC method :meth:`methodCall` that takes an object name,
method name, and arguments, and if the call is permitted by its security
rules, calls the designated method on that object.

.. class:: XMLRPCServerBase(name, host=None, port=5000, logRequests=False)

   *name* is an arbitrary string identifier for the XMLRPC server.

   *host* allows you to override the default hostname to use for this
   server (which defaults to the fully-qualified domain name of this computer).
   Setting it to 'localhost' will typically make the XMLRPC server only accessible
   to processes running on this computer.

   *port* specifies the port number on which this server should run.

   *logRequests* is passed on to :class:`SimpleXMLRPCServer` as
   a flag determining whether it outputs verbose log information.


.. method:: XMLRPCServerBase.__setitem__(name,obj)

   Save *obj* as the service called *name* in this XMLRPC server.
   *obj* must have an :attr:`xmlrpc_methods` dictionary whose
   keys are the names of its methods that XMLRPC clients are allowed
   to call.

.. method:: XMLRPCServerBase.__delitem__(name)

   Delete the service called *name* in this XMLRPC server.

.. method:: XMLRPCServerBase.register(url=None,name='index',server=None)

   Send information describing the services in this XMLRPC server,
   stored by the user on its :attr:`registrationData` attribute,
   to the resource database server, which can be specified in
   several ways.  If *url* is not None, it will make an XMLRPC
   connection to the resource database server using *url* (as the
   URL for the XMLRPC server) and *name* (as the name of the server
   object that stores the resource database dictionary).  Otherwise,
   if *server* is not None, it is assumed to be a resource database
   object (or XMLRPC connection to such a database) providing a
   :meth:`registerServer` method that takes two arguments,
   a *locationKey* and the registration data.  Otherwise,
   it tries to connect to worldbase's default resource database
   by calling its :meth:`registerServer()` method with the
   same arguments.

.. method:: XMLRPCServerBase.serve_forever()

   Start the XMLRPC server, after detaching it from
   stdin, stdout and stderr; this call will never exit.


This XMLRPC server provides several interface methods to
XMLRPC clients contacting it:

.. method:: XMLRPCServerBase.objectList()

   Returns a dictionary of its server objects, whose keys are their
   names, and whose values are in turn dictionaries whose keys are
   their allowed method names.

.. method:: XMLRPCServerBase.objectInfo(objname)

   Returns a dictionary whose keys are the allowed method names for
   the server object named *objname*.

.. method:: XMLRPCServerBase.methodCall(objname,methodname,args)

   Calls the designated method on the named server object, with the
   provided *args*, and returns its result to the XMLRPC client.


Example server objects that can be added to a :class:`XMLRPCServerBase`
include :class:`seqdb.BlastDBXMLRPC`, :class:`xnestedlist.NLMSAServer`.


XMLRPCClient, get_connection
----------------------------
Client for accessing a :class:`XMLRPCServerBase` server.  Provides
a dictionary interface whose keys are names of available server objects,
and whose associated values are client objects that provide a transparent
interface to the server objects (i.e. calling a method on the client
object returns the value of the result of calling the same named method
on the server object).

.. class:: XMLRPCClient(url)

   Makes a connection to the XMLRPC server running on the specified *url*,
   typically consisting of both a host name and port number.

.. method:: XMLRPCClient.__getitem__(name)

   Obtain a client object for the server object specified by *name*.
   It will be decorated with the set of methods on the server object
   that are allowed to be accessed by XMLRPC.

.. function:: XMLRPCClient.get_connection(url, name)

   As a convenience, the :mod:`coordinator` module provides a function
   :func:`get_connection` that provides an efficient connection to XMLRPC
   server objects.  Specifically, it caches past requests, so that multiple
   requests for the same server object will re-use the same client object,
   and requests for different server objects on the same XMLRPC server will
   share the same :class:`XMLRPCClient` connection.  It is simply used as follows:
   ``get_connection(url,name)``, where ``url`` is the URL of the XMLRPC
   server, and ``name" is the name of the server object you wish to access.
   For example::

      myclient = coordinator.get_connection('http://leelab.mbi.ucla.edu:5000','ucsc17')


coordinator Module Functionality Overview
-----------------------------------------

The :mod:`coordinator` module provides a simple system for running a large collection of tasks on a set of cluster nodes.  It assumes:


  
* authentication is handled using ssh-agent.  The coordinator module does no authentication itself; it simply tries to spawn jobs to remote nodes using ssh, assuming that you have previously authenticated yourself to ssh-agent.
  
* the client nodes can access your scripts using the same path as on the initiating system.  In other words, if you launch a coordinator job /home/bob/mydir/myscript.py, your client nodes must also be able to access /home/bob/mydir/myscript.py (e.g. via NFS).
  
* your job consists of a large set of task IDs, and a computation to be performed on each ID.  To run this job, you provide an iterator that generates the list of task IDs for the Coordinator to distribute to your client nodes.  You start your script to run a Coordinator that serves your list of task IDs to the client nodes.  You also provide  a function that performs your desired computation on each task ID it receives from the Coordinator.  Typically, you provide both the server function (i.e. the iterator that generates the list of task IDs) and the client function (that runs your desired computation for each ID) within a single Python script file.  Running this script without extra flags starts the Coordinator, which in turn launches your script as a Processor on one or more client nodes.  The Processors andCoordinator work together to complete all the task IDs.
  
* a ResourceController performs load balancing and resource allocation functions, including: dividing up loads from one or more Coordinators over a set of hosts (each with one or more CPUs); serving a Resource database to Processors requesting specific resources; resource-locking on a per node basis for preventing Processors from using a Resource that is under construction by another Processor.  For very large files that are used repeatedly by your computation, it is preferable to first copy them to local disk on each cluster node (fast), rather than reading them over and over again from NFS (slow).  Resources provide a simple mechanism for doing this.
  

To see how to use this, let's look at an example script, mapclusters5.py::


   from pygr.apps.leelabdb import *
   from pygr import coordinator

   def map_clusters(server,genome_rsrc='hg17',dbname='HUMAN_SPLICE_03',
                    result_table='GENOME_ALIGNMENT.hg17_cluster_JUN03_all',
                    rmOpts=",**kwargs):
       "map clusters one by one"
       # CONSTRUCT RESOURCE FOR US IF NEEDED
       genome = BlastDB(ifile=server.open_resource(genome_rsrc,'r'))
       # LOAD DB SCHEMA
       (clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,alt3Graph,mrna, \
        protein,clusterExons,clusterSplices) = getSpliceGraphFromDB(spliceCalcs[dbname])

       for cluster_id in server:
           g = genomic_seq[cluster_id]
           m = genome.megablast(g,maxseq=1,minIdentity=98,rmOpts=rmOpts) # MASK, BLAST, READ INTO m
           # SAVE ALIGNMENT m TO DATABASE TABLE test.mytable USING cursor
           createTableFromRepr(m.repr_dict(),result_table,clusters.cursor,
                               {'src_id':'varchar(12)','dest_id':'varchar(12)'})
           yield cluster_id # WE MUST FUNCTION AS GENERATOR

   def serve_clusters(dbname='HUMAN_SPLICE_03',
                      source_table='HUMAN_SPLICE_03.genomic_cluster_JUN03',**kwargs):
       "serve up cluster_id one by one"
       cursor = getUserCursor(dbname)
       t = SQLTable(source_table,cursor)
       for id in t:
           yield id

   if __name__=='__main__':
       coordinator.start_client_or_server(map_clusters,serve_clusters,['hg17'],__file__)


Let's analyze the script line by line:


  
* mapclusters() is a client generator function to be run in a Processor on a client node.  It takes one argument representing its connection to the server (a Processor object), and optional keyword arguments read from the command line.  It first does some initial setup (opens a BLAST database and loads a schema from a MySQL database), then iterates over task IDs returned to it from the server.  A few key points:
  
* server.open_resource(genome_rsrc,'r') requests a resource given by the genome_rsrc argument from the ResourceController, does whatever is necessary to copy this resource to local disk, and then opens it for reading, returning a file-like object.  This can then be used however you like, but you MUST call its close() method (just as you should always do for any file object) to indicate that you're done using it.  Failure to close() the file object will leave the Resource "hg17" permanently locked on this specific node.  (You would then have to unlock it by hand using the ResourceController.release_rule() method).
  
* yield cluster_id: the client function must be a Python generator function (i.e. it must use the yield statement), and it must yield the list of IDs that it has processed.  Python's generator construct is extremely convenient for many purposes: here it lets us perform both our initializations and iteration over IDs within a single function, while at the same time wrapping each iteration within the Processor's error trapping code (to prevent a single error in your code from causing the entire Processor to shut down).  The Processor will trap any errors in your code and and send tracebacks to your Coordinator, which will report them in its logfile.  The Processor will tolerate occasional errors and continue processing more IDs.  However, if more than a certain number of IDs in a row fail with errors (controlled by the Processor.max_errors_in_a_row attribute), the Processor will exit, on the assumption that either your code or this specific client node don't work correctly.
  
* serve_clusters() is the server generating function to be run in the Coordinator.  It returns an iterator that generates all the task IDs that we want to run.  Again, the Python generator construct provides a very clean way of doing this: we simply yield each ID that we want to process in our client Processors.
  
* if __name__=="__main__": this final clause automatically launches our script as either a Coordinator or Processor depending on the command line options (which are automatically parsed by start_client_or_server()).  All we have to do is pass the client generator function, the server generator function, a list of the resources this job will use, and the name of the script file to be run on client nodes.  Since that is just this script itself, we use the Python builtin symbol __file__ (which just evaluates to the name of the current script).
  
* Command-line arguments are parsed (GNU-style, ie. --foo=bar) by start_client_or_server() and passed to your client and server functions as Python named parameters.  Because the same list of arguments is passed to your client and server functions, and each of these functions won't necessarily want to get all the named arguments, you should include the **kwargs at the end of the argument list.  Any unmatched arguments will be stored in kwargs as a Python mapping (dictionary).  If you fail to do this, your client or server function will crash if called with any named parameters other than the ones it expects.


Log and Error Information
-------------------------

Process logging and error information go to three different types of logs:


  
* Processor logfile(s): every individual Processor (and all subprocesses run by it) send stdout and stderr to a logfile on local disk of the host on which it is running.  Currently the filename is /usr/tmp/NAME_N.log, where NAME is the name you assigned to the job when you started the Coordinator, and N is the numeric ID of the Processor assigned by the coordinator (just an auto-increment integer beginning at 0, and increasing by one for each Processor the Coordinator starts).  This logfile is the place to look if your job is failing mysteriously--look in the logfile and see its last words before its demise.  You can get a complete list of the logfiles for all the Coordinator's Processors by inspecting the logfile attribute of the CoordinatorMonitor (see below).
  
* Coordinator logfile: all XMLRPC requests from client Processors, as well as error messages from them, are logged here.  All Python errors (tracebacks) in your client (Processor) code are reported here.  Also, the actual SSH commands used to invoke your Processors on cluster nodes, are logged here.  This is usually the place to start, to see whether things are going well (you should see a long stream of next requests as Processors finish a task and request the next one), or failing with errors.
  
* ResourceController logfile: all XMLRPC requests from Processors and Coordinatorsare logged here, including register() and unregister(), resource requests, and load reporting from cluster nodes.  If things are working well, you should see a stream of regular report_load() messages showing steady, full utilization of all the host processors.  Excessive register/unregister churning (jobs that start and immediately exit) is a common sign of trouble with your jobs.
  

Coordinator
-----------

To start a job coordinator (which in turn will the run the whole job by starting Processors on cluster nodes using SSH)::

   python mapclusters5.py mm5_jan02 --errlog=/usr/tmp/leec/mm5_jan02.log \
     --dbname=MOUSE_SPLICE --source_table=genomic_cluster_jan02 \
     --genome_rsrc=mm5 --result_table=GENOME_ALIGNMENT.mm5_cluster_jan02_all \
     --rmOpts=-rodent \


Here we have told the Coordinator to name itself "mm5_jan02" in all its communications with the ResourceController.  Since we gave no command-line flags, the Coordinator will assume that a ResourceController is already running on port 5000 of the current host.    You must have an ssh-agent running BEFORE you start the Coordinator, since the Coordinator will attempt to spawn jobs using SSH.  The Coordinator will exit with an error message if it is unable to connect to ssh-agent.  A few notes:


  
* The Coordinator will run as a demon process (i.e. in the background, and detached from your terminal session), and redirect its  output into a file (here, given by the --errlog option). If you don't specify an --errlog filename, it will create a filename determined by the name we told it to run as, in this case "mm_jan02.log".
  
* You must ensure that SSH can launch processes on your client nodes "unattended" i.e. without a connection to a controlling terminal.  If SSH has to ask for userconfirmations when connecting to a given host (e.g. if it asks whether you want to accept the host key), the Coordinator will not be able to use that host.
  
* Python errors (tracebacks) in your will be GNU-style command-line options (e.g. --port=8889) are automatically parsed by start_client_or_server() and passed to the Coordinator.__init__() as keyword arguments.  This constructor takes the following optional arguments:
      \begin{itemize}
*     port: the port number on which this Coordinator should run
  
*     priority: a floating point number specifying the priority level at which this Coordinator should be run by the ResourceController.  The default value is 1.0.  A value of 2.0 will give it twice as many Processors as a competing Coordinator of priority 1.0.
  
*     rc_url: the URL for the ResourceController.  Defaults to http://THISHOST:5000
*     errlog: logfile path for saving all output to.  Defaults to NAME.log, where NAME is the name you assigned to this Coordinator. Can be an absolute path.
  
*     immediate: if True, make the job run immediately, without waiting for previous jobs to finish.  Default: False.
  
*     demand_ncpu: if set to a non-zero value, specifies the exact number of Processors you want to run your job.
  
*     NB: command line arguments are also passed to your server function, and to your client function, as Python named parameters.  See the mapclusters5.py example above.

\end{itemize}

ResourceController
------------------

Whereas you start a separate Coordinator for each set of jobs you want to run, you only need a single ResourceController running. To start the ResourceController, run::

   python coordinator.py --rc=bigcheese


This starts the ResourceController (running as a demon process in the background) and names it "bigcheese"; a name argument (given by the --rc flag) is REQUIRED.  Since you didn't specify command-line flags, it will run on the default port 5000.  It will use several files based on the name you gave it:

  
* bigcheese.hosts: a list of cluster nodes and associated maximum load (separated by whitespace, one pair per line).  It will attempt to fill these nodes with jobs, up to the maximum load level specified for each, sharing the load between whatever set of Coordinators contact it.
  
* bigcheese.log: all output from the ResourceController (showing requests made to it by Coordinators and Processors) is logged to this file.
  
* bigcheese.rules: this file is a Python shelve created by the ResourceController as its rules database.
  
* bigcheese.rsrc: this file is a Python shelve created by the ResourceController as its resource database.GNU-style command-line options (e.g. --port=5001) are automatically parsed by start_client_or_server() and passed to the ResourceController.__init__() as keyword arguments.  This constructor takes the following optional arguments:
  
* port: the port number on which this ResourceController should run
  
* overload_margin: how much "extra" load above the standard level is allowable.  This prevents temporary load spikes from causing Processors to exit.  Set by default to 0.6.  I.e. if the maxload for a host was set to 2.0, any load above 2.6 would cause the ResourceController to start shutting down Processor(s) on that host.
  
* rebalance_frequency: the time interval, in seconds, for rerunning the ResourceController.load_balance() method.  Defaults to 1200 sec.
  
* errlog: logfile path for saving all output to.  Defaults to NAME.log, where NAME is the name you assigned to this ResourceController. Can be an absolute path.
  


RCMonitor
---------

The coordinator module also provides a convenience interface for interrogating and controlling jobs.  In an interactive Python shell, import the coordinator module, and create an RCMonitor object::

   from pygr import coordinator
   m = coordinator.RCMonitor()


Since you did not specify any arguments, it will default to searching for the ResourceController on the current host, port 5000.  You can specify a host and or port as additional arguments.  It also loads an index of coordinators currently registered with this ResourceController, accessible on its coordinators attribute::

   for name,c in m.coordinators.items():
     print name,len(c.client_report)


will print a list of the coordinators and how many Processors each is currently running.  Each coordinator is represented by a CoordinatorMonitor object in this coordinators index.

Both RCMonitor and CoordinatorMonitor objects give you access to the XMLRPC methods of the ResourceController and Coordinators they represent.  That is, running a method on the RCMonitor actually runs the identically-named method on the ResourceController.  Some of the most useful ResourceController methods are:


  
* report_load(host,pid,load): inform RC that the current load on host is load.
  
* load_balance(): make the RC rebalance load, using all available nodes and coordinators
  
* setrule(rsrc,rule): set a production rule for the resource named rsrc.  rule must be a tuple consisting of the local filepath to be used for the resource, and a shell command that will construct it, with a %s where you want the filename to be filled in.
  
* delrule(rsrc): deletes the rule for rsrc from the rules database.
  
* set_hostinfo(host,attr,val) set an attribute for host.  For example, to set the maximum load for this host: rcm.set_hostinfo(host,'maxload',2.0).  This should usually be the number of CPUs on this host.  NB: these settings will apply only to the current ResourceController, and are not saved back to its NAME.hosts file.  If you want to make these settings permanent (i.e. to apply to ResourceControllers you start anew in the future), then edit the NAME.hosts file.
  
* retry_unused_hosts(): make the RC search its hosts database for hosts that are not currently in use (e.g. jobs may have died) and try to reallocate them to the existing coordinators.
  

Both RCMonitor and CoordinatorMonitor objects have a get_status() method that updates them with the latest information from their associated ResourceController or Coordinator.

Here are some typical monitor usages::

   c = m.coordinators['mapclusters3'] # GET MY COORDINATOR
   c.client_report.sort() # MAKE IT SORT CLIENTS BY HOSTNAME
   c.client_report # PRINT THE SORTED LIST, SHOWING HOST, PID, #TASKS DONE
   c.pending_report # PRINT LIST OF TASK IDS CURRENTLY RUNNING
   c.nsuccess # PRINT TOTAL #TASKS DONE
   c.nerrors  # PRINT TOTAL #TASKS FAILED
   c.logfile # PRINT LIST OF ALL PROCESSOR LOGFILES

   m.rules # PRINT THE CURRENT RULES DATABASE
   m.resources # PRINT THE CURRENT RESOURCES DATABASE
   m.setrule('hg17',
   ('/usr/tmp/ucsc_msa/hg17',
   'gunzip -c /data/yxing/databases/ucsc_msa/human_assembly_HG17/*.fa.gz
   >%s'))
   m.get_status() # UPDATE OUR RC INFO
   m.set_hostinfo('llc22','maxload',2.0) # ADD A NEW HOST TO OUR DATABASE
   m.setload('llc1','maxload',0.0) # STOP USING llc1 FOR THE MOMENT
   m.load_balance() # MAKE IT ALLOCATE ANY FREE CPUS NOW...
   m.locks # SHOW LIST OF RESOURCES CURRENTLY LOCKED, UNDER CONSTRUCTION


Security
--------

Internal communication between Processors, Coordinators and ResourceController is performed using XMLRPC and thus is not secure. However, since no authentication information or actual commands are transmitted by XMLRPC, and the coordinator module does not enable the processes that use it to do anything that they are not ALREADY capable of doing on their own (i.e. spawn ssh processes), the main security vulnerabilty is Denial Of Service (i.e. an attacker listening to the XMLRPC traffic could send messages causing Processors to shutdown, or Coordinators to be blocked from running any Processors).  In other words the security philosophy of this module is to avoid compromising your security, by leaving the security of process invocation entirely to your existing security mechanisms (i.e. ssh and ssh-agent).  Commands are only sent using SSH, not XMLRPC, and the XMLRPC components are designed to prevent known ways that an XMLRPC caller might be able to run a command on an XMLRPC server or client. (I blocked known security vulnerabilities in Python's SimpleXMLRPCServer module).

In the same spirit, the current implementation does not seek to block users from issuing commands that could let them "hog" resources, for the simple reason that in an SSH-enabled environment, they would be able to do so regardless of this module's policy.  I.e. the user can simply not use this module, and spawn lots of processes directly using SSH.  In the current implementation, every user can send directives to the ResourceController that affect resource allocation to other users' jobs.  This means everybody has to "play nice", only giving their Coordinator(s) higher priority if it is really appropriate and agreed by other users.  Unless a different process invocation mechanism (other than SSH by each user) were adopted, it doesn't really make sense to me to try to enforce a policy that is stricter than the policy of the underlying process invocation mechanism (i.e. SSH).  Since every user can use SSH to spawn as many jobs as they want, without regard for sharing with others, making this module's policy "strict" doesn't really secure anything.

