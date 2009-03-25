Using Pygr as a Graph Database
------------------------------
The real power of Pygr is that it provides a simple model for viewing
all data as *graph databases*-- in which all data are represented
as nodes and connections between nodes (edges), and queries are formulated
as a specific pattern of connections to find --
in a very Pythonic style.  To illustrate the simplicity and power
of the graph database approach, Pygr has a strong emphasis
on bioinformatics applications ranging from genome-wide analysis of
alternative splicing patterns, to comparative genomics queries of
multi-genome alignment data.

The following introductory examples show how to use Pygr for graph queries, sequence searching and alignment queries, annotation queries, and multigenome alignment queries.


Example: Simple graph query
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Why would you want to use Pygr?  Interesting data often consists of specific graph structures, and these relationships are much easier to describe as graphs than they are in SQL.  For example, the simplest and most common form of alternative splicing is exon-skipping, where an exon is either skipped or included (see slide 15 of the ISMB slides for a picture).  This can be defined immediately as a graph in which three nodes (exons 1, 2, 3) are joined by edges either as 1-2-3 or 1-3.  Unfortunately, writing an SQL query for this simple pattern requires a 6-way JOIN (argh)::

   SELECT * FROM exons t1, exons t2, exons t3, splices t4, splices t5, splices t6
   WHERE t1.cluster_id=t4.cluster_id AND t1.gen_end=t4.gen_start
     AND t4.cluster_id=t2.cluster_id AND t4.gen_end=t2.gen_start
     AND t2.cluster_id=t5.cluster_id AND t2.gen_end=t5.gen_start
     AND t5.cluster_id=t3.cluster_id AND t5.gen_end=t3.gen_start
     AND t1.cluster_id=t6.cluster_id AND t1.gen_end=t6.gen_start
     AND t6.cluster_id=t3.cluster_id AND t6.gen_end=t3.gen_start;


Such a six-way JOIN is painfully slow in a relational database; in general such queries just aren't practical.  More fundamentally, the relational schema is forced to represent the graph relation with combinations of foreign keys and other data that the user really should not have to remember.  All the user should know is that there is a specific relation, e.g. from this exon, the "next" exon is X, and the relation joining them is splice Y.

In Pygr, writing the query is just a matter of writing down the graph (edges from 1 to 2, 1 to 3, and 2 to 3, but no special "edge information")::

   queryGraph = {1:{2:None,3:None},2:{3:None},3:{}}


We can now execute the query using the GraphQuery class::

   results = [dict(m) for m in GraphQuery(spliceGraph,queryGraph)]


This is more or less equivalent to writing a bunch of for-loops for iterating over the possible closures::

   results = []
   for e1 in spliceGraph: # FIND ALL EXONS
       for e2 in spliceGraph[e1]: # NEXT EXON
           for e3 in spliceGraph[e2]: # NEXT EXON
               if e3 in spliceGraph[e1]: # MAKE SURE SPLICE FROM e1 -> e3
                   results.append({1:e1,2:e2,3:e3}) # OK, SAVE MATCH


It is often convenient to bind an object attribute to a graph, so that you can use either the graph syntax or a traditional object attribute and mean exactly the same thing.  In the splice graph example, we bind the exon.next attribute to the spliceGraph, so the above for-loops can also be written::

   results = []
   for e1 in spliceGraph: # FIND ALL EXONS
       for e2 in e1.next: # NEXT EXON
           for e3 in e2.next: # NEXT EXON
               if e3 in e1.next: # MAKE SURE SPLICE FROM e1 -> e3
                   results.append({1:e1,2:e2,3:e3}) # OK, SAVE MATCH


Another interesting query in the alternative splicing field is the so-called U12-adapter exon query (see slide 21 of the ISMB slides)::

   queryGraph = {0:{1:dict(dataGraph=alt5Graph),
                    2:dict(filter=lambda edge,**kwargs:edge.type=='U11/U12')},
                 1:{3:None},
                 2:{3:None},
                 3:{}}


Here we use edge information in the query graph to add a few constraints:


* the dataGraph argument tells the query to search for exon 1 from exon 0 using a different graph (alt5Graph).
  
* the filter argument provides a function that returns True only if the edge between exon 0 and exon 2 is of type U11/U12.  Therefore the query will only match sp
  lice graphs that have a U12 splice between this pair of exons.
  


Note that the query graph "nodes" (in this example, the integers 0, 1, 2, 3) are
quite arbitrary.  We could have used strings, or other kinds of objects instead.

Now if we want to see the results right away, we use the mapping returned by GraphQuery to look at individual nodes and edges of the dataGraph that matched our query::

   for m in GraphQuery(spliceGraph,queryGraph):
       print m[1].id,m[0,2].id # PRINT EXON ID FOR EXON 1,
                               # SPLICE ID FOR SPLICE 0 -> 2


The match is returned by GraphQuery as a mapping from nodes and edges of the query graph to nodes and edges of the data graph.  Edges are specified simply as tuples of the nodes you want to get the edge for (in this example 0,2).
Constructing a Graph
How was the spliceGraph created in the first place?  Let's say we have an initial list of tuples giving connections between exon objects and splice objects, where each tuple consists of a pair of exons connected by a splice::

   for exon1,exon2,splice in spliceConnections:
       spliceGraph += exon1 # add exon1 as a node in the graph
       spliceGraph += exon2 # if already a node in the graph, does nothing...
       exon1.next[exon2] = splice # add an edge, with splice as the edgeinfo


The last operation makes use of the binding of exon.next to spliceGraph, and is equivalent to::

   spliceGraph[exon1][exon2] = splice


If we didn't want to save the edge information, we could use the simpler syntax::

   spliceGraph[exon1] += exon2 # equivalent to exon1.next+=exon2


This "short" form is equivalent to saving None as the edge information.


Alignment Query as a Graph Database Query
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pygr can do much more sophisticated analyses than this fairly easily.
Just to give a taste of how to use these capabilities, we will illustrate
one example of a standard Pygr model: querying Pygr data by drawing a "query
graph" showing the connections we want to find, and running its GraphQuery()
engine.  Since Pygr alignments follow the same interface as any Pygr graph, we can query them using the standard GraphQuery class.  Let's say we have a Python script load_alignments.py that loads two alignments:


  
* mRNA_swiss: an alignment of mRNA sequences to homologous SwissProt sequences;
  
* swiss_features: an alignment of SwissProt sequences onto annotation objects.
  

To find out how the known SwissProt annotations map on to our mRNA sequences requires a join, which can be formulated as a simple Pygr graph, consisting of a mapping of an mRNA sequence interval (node 1), onto a SwissProt sequence interval (node 2), onto a feature annotation (node 3)::

   >>> from load_alignments import * # load the alignments
   >>> from pygr.graphquery import *      # import the graph query code
   # draw a graph using a dict.  Note: edge 2->3 must come from swiss_features
   >>> queryGraph = {1:{2:None},2:{3:dict(dataGraph=swiss_features)},3:{}}
   # run the query and save the mappings
   >>> l = [dict(d) for d in GraphQuery(mRNA_swiss,queryGraph)]
   >>> len(l) # how many annotations mapped onto our mRNA sequences?
   4703


We assumed that mRNA_swiss would be passed as the default dataGraph, and specified directly that edge 2->3 should be looked up in swiss_features.  We then captured all the results from the GraphQuery iterator using a Python list comprehension.  Note that since the iterator returns each result in the same container (mapping object), if we want to save all the individual results we have to copy each one to a new mapping (dict) object, as illustrated in this example.
Storing Alignments in a Relational Database


Example: a MySQL Database OBSOLETE
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Here's an example of working with sequences from a relational database::

   >>> import MySQLdb # standard module for accessing MySQL, now get a cursor...
   >>> rdb = MySQLdb.connect(db='HUMAN_SPLICE_03',read_default_file=os.environ['HOME'
   ]+'/.my.cnf')
   >>> t = SQLTable('genomic_cluster_JUN03',rdb.cursor()) #interface to a table of
    sequences
   >>> from pygr.seqdb import *   # pygr module for working with sequences from databases
   >>> t.objclass(DNASQLSequence) #use this class as "row objects"
   >>> s2 = t['Hs.1162'] # get a specific sequence object by ID
   >>> str(s2[1000:1050]) # this will only get 50 nt of the genomic sequence from
   MySQL
   'acctgggtgatgaaataaatttttacgccaaatcccgatgacacacaatt'


(Note: in this example we used MySQLdb.connect()'s ability to read database
server and user authentication information directly from the standard ~/.my.cnf file normally used by the MySQL client).

