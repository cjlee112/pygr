#!/usr/bin/python

import re
import sys
import string
import math


def print_interval(mode,hit_id,subj_seq,subject_id,blast_score,e_value,identity_percent,blast_frame,query_start,query_end,subj_start,subj_end,q_interval_start,i_query,s_interval_start,i_subj,output):
   if (mode == "all"):

      identity_percent = re.sub("%","",identity_percent)

      if (int(blast_frame)>=0):
          match = "MATCH_INTERVAL\t%d\t%s\t%s\t%d\t%.5f\t%s\t%s\t%d\t%d\t%d\n" %(hit_id,subj_seq,subject_id,float(blast_score),e_value,identity_percent,blast_frame,q_interval_start,i_query-q_interval_start,int(s_interval_start))
          output += match
      else:
         match = "MATCH_INTERVAL\t%d\t%s\t%s\t%d\t%.5f\t%s\t%s\t%d\t%d\t%d\n" %(hit_id,subj_seq,subject_id,float(blast_score),e_value,identity_percent,blast_frame,q_interval_start,i_query-q_interval_start,i_subj-int(blast_frame))
         output += match

   elif (mode == "detail"):
      match = "%d\t%d\t%d\t%d\t%d\n" %(hit_id,q_interval_start,i_query-1,s_interval_start,i_subj-blast_frame)
      output += match

   return output

def print_hit(mode,hit_id,seq_id,subject_id,blast_score,e_value,identity_percent,blast_frame,query_start,query_end,subj_start,subj_end,query_seq,subj_seq,output):

   query_len=len(query_seq)
   q_interval_start = -1
   i_query=query_start

   if(int(blast_frame)>0):
      i_subj=subj_start

   else:
      i_subj=subj_end
 
   i = 0 

   while(i<(query_len)):

      if (query_seq[i] == "-"):

         if(q_interval_start>0):
           output = print_interval(mode,hit_id,seq_id,subject_id,blast_score,e_value,identity_percent,blast_frame,query_start,query_end,subj_start,subj_end,q_interval_start,i_query,s_interval_start,i_subj,output)

         q_interval_start = -1
         i_subj += int(blast_frame)
 
      else:

         if(subj_seq[i] == "-"):

            if(q_interval_start>0):
               output = print_interval(mode,hit_id,seq_id,subject_id,blast_score,e_value,identity_percent,blast_frame,query_start,query_end,subj_start,subj_end,q_interval_start,i_query,s_interval_start,i_subj,output)
  
            q_interval_start = -1
    
         else:
            if(q_interval_start < 0):
               q_interval_start=i_query
               s_interval_start=i_subj
            i_subj += int(blast_frame)
     
         i_query += 1
      i += 1 

   if (q_interval_start>0):
  
       output = print_interval(mode,hit_id,seq_id,subject_id,blast_score,e_value,identity_percent,blast_frame,query_start,query_end,subj_start,subj_end,q_interval_start,i_query,s_interval_start,i_subj,output)

   query_seq = re.sub("-","",query_seq) 
   subj_seq = re.sub("-","",query_seq)

   if(mode =="summary"):
      print("%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n",hit_id,seq_id,subject_id,blast_score,e_value,identity_percent,blast_frame,query_start,query_end,subj_start,subj_end)
   query_start=9999999999
   query_end=-1
   subj_start=9999999999
   subj_end=-1
   
   return query_start,query_end,subj_start,subj_end,output



def parse_blast(fd,mode):

   hit_id = 0 
   output = "" 
   rbuf = 0 
   dbuf = ""
 
   while(rbuf != ""):
      rbuf = fd.read(1024)
      dbuf += rbuf

   dbuf = dbuf.split("\n")

   for i in dbuf:

      seq = re.search(r"^Query=.*",i)
      if (seq): 
          init_query_data = seq.group(0).split(" ")
          seq_id = init_query_data[1]
          query_start= 9999999999
          query_end = -1
          subj_start = 9999999999
          subj_end = -1

      seq =  re.search(r"^>.*",i)
      if (seq):
         if(query_start < query_end):
            hit_id += 1  
            query_start,query_end,subj_start,subj_end,output = print_hit(mode,hit_id,seq_id,subject_id,blast_score,e_value,identity_percent,blast_frame,query_start,query_end,subj_start,subj_end,query_seq,subj_seq,output)
         subject_data = seq.group(0).split(" ")
         subject_id = subject_data[0][1:]
         r_subject_title = "" 

         for i in subject_data[1:]:
           r_subject_title += i + " "   
   
         subject_title = string.strip(r_subject_title)
         blast_frame="+1"

      seq = re.search(r"^ Score =.*",i)
      if(seq):
         if (query_start < query_end):
            hit_id += 1  
            query_start,query_end,subj_start,subj_end,output = print_hit(mode,hit_id,seq_id,subject_id,blast_score,e_value,identity_percent,blast_frame,query_start,query_end,subj_start,subj_end,query_seq,subj_seq,output)

         blast_field = 3
         e_field = 8
         score_data = seq.group(0).split(" ")

         while (score_data[blast_field] == ""):
            blast_field += 1
            e_field += 1  
         blast_score = score_data[blast_field]
         e_value = score_data[e_field]
         if (re.search("e",e_value)):
            e_value = "1" + e_value
         if (float(e_value) + 0.0 == 0.0):
            e_value = 300               
         else:
            e_value = -math.log(float(e_value)+0.0)/math.log(10.0);
            if str(e_value) == "inf":
               e_value = 300
      
         e_value = float(str(e_value))
   
         query_seq = ""
         subj_seq = "" 
         subj_start=9999999999
         subj_end= -1         

      seq = re.search(r"^  Database:.*",i)
      if (seq):
         if(query_start < query_end):
            hit_id += 1
            query_start,query_end,subj_start,subj_end,output = print_hit(mode,hit_id,seq_id,subject_id,blast_score,e_value,identity_percent,blast_frame,query_start,query_end,subj_start,subj_end,query_seq,subj_seq,output)
         db_data = seq.group(0).split(" ")

      seq = re.search(r"Identities =.*",i)
      if (seq):
         ident_data = seq.group(0).split(" ")
         identity_percent = ident_data[3][1:len(ident_data[3])-2]

      seq = re.search(r"^ Frame =.*",i)
      if (seq):
         frame_data = seq.group(0).split(" ")
         blast_frame = frame_data[len(frame_data) - 1]

      seq = re.search(r"^ Strand =.*",i)
      if (seq):
         strand_data = seq.group(0).split(" ") 
         strand = strand_data[5]
         if (strand == "Plus"):
            blast_frame ="+1"
         if (strand == "Minus"):
            blast_frame = "-1"

      seq = re.search(r"^Query:.*",i)
      if (seq):
         query_data = seq.group(0).split(" ") 
         query_s = int(query_data[1])
         query_e = int(query_data[len(query_data)-1])
         if query_s < query_start:
      	    query_start = query_s
         if query_e <= query_start:
            query_start = query_e 
         if query_s >= query_end:
            query_end <= query_s 
         if query_e >= query_end: 
            query_end = query_e
         query_seq = string.strip(query_seq + " " + query_data[len(query_data) - 2])
         query_seq = re.sub(" ","",query_seq)

      seq = re.search(r"^Sbjct:.*",i)
      if (seq):
         subj_data = seq.group(0).split(" ")
         sub_s = int(subj_data[1])
         sub_e = int(subj_data[len(subj_data)-1])
         if sub_s <= subj_start:
            subj_start = sub_s
         if sub_e <= subj_start:
            subj_start = sub_e
         if sub_s >= subj_end:
            subj_end = sub_s
         if sub_e >= subj_end:
            subj_end = sub_e 
         subj_seq = subj_seq + " " + subj_data[len(subj_data) - 2]
    
   for i in output.split("\n"):
      if (i != ""):
         yield i 

if __name__ == "__main__":
 
   for i in parse_blast(open("/dev/stdin"),"all"):
      print i
