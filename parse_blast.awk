#!/usr/bin/awk -f




function is_repetitive_hit(start,end,threshold,threshold2)
{
  overlap[0]= -1;
  overlap[1]= -10;

  if (region[0]>=start && region[0]<end) {
    overlap[0]=region[0];
    extent[0]=start;
  }
  else if (start>=region[0] && start<region[1]) {
    overlap[0]=start;
    extent[0]=region[0];
  }
  else { # WE HAVE NO OVERLAP, SO JUST RESET AND RETURN */
    region[0]= start; # SAVE THE CURRENT REGION FOR CHECKING THE NEXT ONE*/
    region[1]= end;
    return 0;  # NO REPETITIVE OVERLAP */
  }
  if (region[1]>=start && region[1]<end) {
    overlap[1]=region[1];
    extent[1]=end;
  }
  else {
    overlap[1]=end;
    extent[1]=region[1];
  }
  if (overlap[0]>=0) { # GOT OVERLAP */
    my_length=end-start;
    if (overlap[1]-overlap[0]>threshold*my_length && overlap[1]-overlap[0]>threshold2*(region[1]-region[0])) {
#      printf("REPEAT [%d,%d]: overlaps [%d,%d]\n",start,end,region[0],region[1]);
      region[0]=extent[0]; # SAVE THE UNION OF THE OVERLAPPING REGIONS*/
      region[1]=extent[1];
      return 1; # THIS IS A REPEAT!*/
    }
  }

  region[0]= start; # SAVE THE CURRENT REGION FOR CHECKING THE NEXT ONE*/
  region[1]= end;
  return 0;  # NO REPETITIVE OVERLAP */
}





function print_interval()
{
    if (mode=="all") {
	if (IDENTITY_PERCENT+0<identity_min) {
	    return;
	}
	if (BLAST_FRAME+0>=0) {
	    printf("MATCH_INTERVAL\t%d\t%s\t%s\t%d\t%s\t%s\t%s\t%d\t%d\t%d\n",hit_id,SEQ_ID,SUBJ_ID,BLAST_SCORE+0,E_VALUE,IDENTITY_PERCENT,BLAST_FRAME,q_interval_start,i_query-q_interval_start,s_interval_start);
	}
	else {
	    printf("MATCH_INTERVAL\t%d\t%s\t%s\t%d\t%s\t%s\t%s\t%d\t%d\t%d\n",hit_id,SEQ_ID,SUBJ_ID,BLAST_SCORE+0,E_VALUE,IDENTITY_PERCENT,BLAST_FRAME,q_interval_start,i_query-q_interval_start,i_subj-BLAST_FRAME);
	}
    }
    else if (mode=="detail") {
	printf("%d\t%d\t%d\t%d\t%d\n",hit_id,q_interval_start,i_query-1,s_interval_start,i_subj-BLAST_FRAME);
    }
}




function print_hit()
{
  if (remove_repeats) {
    if (is_repetitive_hit(QUERY_START,QUERY_END,0.9,0.8)) {
      if (nrepeat++ > 20) {
	printf("REMOVING REPEAT %d-%d\n",QUERY_START,QUERY_END);
        return 0;
      }
    }
    else {
      nrepeat=0;
    }
  }
    hit_id++;
    query_len=length(QUERY_SEQ);
    q_interval_start= -1;
    i_query=QUERY_START;
    if (BLAST_FRAME+0>0) {
	i_subj=SUBJ_START;
    }
    else {
	i_subj=SUBJ_END;
    }
    for (i=1;i<=query_len;i++) {
	if (substr(QUERY_SEQ,i,1)=="-") {
	    if (q_interval_start>0) {
		print_interval();
	    }
	    q_interval_start= -1;
	    i_subj+= BLAST_FRAME;
	}
	else {
	    if (substr(SUBJ_SEQ,i,1)=="-") {
		if (q_interval_start>0) {
		    print_interval();
		}
		q_interval_start= -1;
	    }
	    else {
		if (q_interval_start<0) {
		    q_interval_start=i_query;
		    s_interval_start=i_subj;
		}
		i_subj+= BLAST_FRAME;
	    }
	    i_query++;
	}
    }
    if (q_interval_start>0) {
	print_interval();
    }
    gsub("-","",QUERY_SEQ);
    gsub("-","",SUBJ_SEQ);
    if (mode=="summary") {
	printf("%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n",hit_id,SEQ_ID,SUBJ_ID,BLAST_SCORE,E_VALUE,IDENTITY_PERCENT,BLAST_FRAME,QUERY_START,QUERY_END,SUBJ_START,SUBJ_END);
    }
    QUERY_START=9999999;
    QUERY_END= -1;
    SUBJ_START=9999999;
    SUBJ_END= -1;
}



/^Query=/ {
    SEQ_ID=$2;
    TITLE=substr($0,index($0,$3));
    QUERY_START=9999999;
    QUERY_END= -1;
}

/No hits/ {
}


/^>/ {
    if (QUERY_START<QUERY_END) {
	print_hit();
    }
    SUBJ_ID=substr($1,2);
    SUBJ_TITLE=substr($0,index($0,$2));
    BLAST_FRAME="+1"
}

/^ Score =/ {
    if (QUERY_START<QUERY_END) {
	print_hit();
    }
    BLAST_SCORE=$3;
    E_VALUE=$8;
    if (substr(E_VALUE,1,1)=="e") {
	E_VALUE="1" E_VALUE;
    }
    if (E_VALUE+0.0 == 0.0) {
	E_VALUE=300;
    }
    else {
	E_VALUE= -log(E_VALUE+0.0)/log(10.0);
	if (E_VALUE=="inf") {
	    E_VALUE=300;
	}
    }
    QUERY_SEQ="";
    SUBJ_SEQ="";
    SUBJ_START=9999999;
    SUBJ_END= -1;
}


/^  Database:/ {
    if (QUERY_START<QUERY_END) {
	print_hit();
    }
}


/Identities =/ {
    IDENTITY_PERCENT=substr($4,2);
    IDENTITY_PERCENT=substr(IDENTITY_PERCENT,1,index(IDENTITY_PERCENT,"%")-1);
}


/^ Frame =/ {
    BLAST_FRAME=$3;
}


/^ Strand = / {
    if ($5=="Plus") {
	BLAST_FRAME="+1";
    }
    else if ($5=="Minus") {
	BLAST_FRAME="-1";
    }
}


/^Query:/ {
    if ($2<QUERY_START) {
	QUERY_START=$2;
    }
    if ($4<QUERY_START) {
	QUERY_START=$4;
    }
    if ($2>QUERY_END) {
	QUERY_END=$2;
    }
    if ($4>QUERY_END) {
	QUERY_END=$4;
    }
    QUERY_SEQ=QUERY_SEQ $3;
}


/^Sbjct:/ {
    if ($2<SUBJ_START) {
	SUBJ_START=$2;
    }
    if ($4<SUBJ_START) {
	SUBJ_START=$4;
    }
    if ($2>SUBJ_END) {
	SUBJ_END=$2;
    }
    if ($4>SUBJ_END) {
	SUBJ_END=$4;
    }
    SUBJ_SEQ=SUBJ_SEQ $3;
}
