from __future__ import generators
import math
from nlmsa_utils import CoordsGroupStart, CoordsGroupEnd

# AUTHORS: zfierstadt, leec


def is_line_start(token, line):
    "check whether line begins with token"
    return token == line[:len(token)]


def get_ori_letterunit(start, end, seq, gapchar='-'):
    """try to determine orientation (1 or -1) based on whether start>end,
    and letterunit (1 or 3) depending on the ratio of end-start difference
    vs the actual non-gap letter count.  Returns tuple (ori,letterunit)"""
    if end > start:
        ori = 1
    else:
        ori = -1
    ngap = 0
    for l in seq:
        if l == gapchar:
            ngap += 1
    seqlen = len(seq) - ngap
    if ori * float(end - start) / seqlen > 2.0:
        letterunit = 3
    else:
        letterunit = 1
    return ori, letterunit


class BlastIval(object):

    def __repr__(self):
        return '<BLAST-IVAL: ' + repr(self.__dict__) + '>'


class BlastHitParser(object):
    """reads alignment info from blastall standard output.
    Method parse_file(fo) reads file object fo, and generates tuples
    suitable for BlastIval."""
    gapchar = '-'

    def __init__(self):
        self.hit_id = 0
        self.nline = 0
        self.reset()

    def reset(self):
        "flush any alignment info, so we can start reading new alignment"
        self.query_seq = ""
        self.subject_seq = ""
        self.hit_id += 1

    def save_query(self, line):
        self.query_id = line.split()[1]

    def save_subject(self, line):
        self.subject_id = line.split()[0][1:]

    def save_score(self, line):
        "save a Score: line"
        self.blast_score = float(line.split()[2])
        s = line.split()[7]
        if s[0] == 'e':
            s = '1' + s
        try:
            self.e_value = -math.log(float(s)) / math.log(10.0)
        except (ValueError, OverflowError):
            self.e_value = 300.

    def save_identity(self, line):
        "save Identities line"
        s = line.split()[3][1:]
        self.identity_percent = int(s[:s.find('%')])

    def save_query_line(self, line):
        "save a Query: line"
        c=line.split()
        self.query_end=int(c[3])
        if not self.query_seq:
            self.query_start=int(c[1])
            # Handle forward orientation.
            if self.query_start < self.query_end:
                self.query_start -= 1
        self.query_seq+=c[2]
        self.seq_start_char=line.find(c[2], 5) # IN CASE BLAST SCREWS UP Sbjct:

    def save_subject_line(self, line):
        "save a Sbjct: line, attempt to handle various BLAST insanities"
        c=line.split()
        if len(c)<4: # OOPS, BLAST FORGOT TO PUT SPACE BEFORE 1ST NUMBER
            # THIS HAPPENS IN TBLASTN... WHEN THE SUBJECT SEQUENCE
            # COVERS RANGE 1-1200, THE FOUR DIGIT NUMBER WILL RUN INTO
            # THE SEQUENCE, WITH NO SPACE!!
            c = ['Sbjct:', line[6:self.seq_start_char]] \
               + line[self.seq_start_char:].split() # FIX BLAST SCREW-UP
        self.subject_end=int(c[3])
        if not self.subject_seq:
            self.subject_start = int(c[1])
            # Handle forward orientation.
            if self.subject_start < self.subject_end:
                self.subject_start -= 1
        self.subject_seq += c[2]
        lendiff = len(self.query_seq) - len(self.subject_seq)
        if lendiff > 0: # HANDLE TBLASTN SCREWINESS: Sbjct SEQ OFTEN TOO SHORT!
            # THIS APPEARS TO BE ASSOCIATED ESPECIALLY WITH STOP CODONS *
            self.subject_seq += lendiff * 'A' # EXTEND TO SAME LENGTH AS QUERY
        elif lendiff < 0 and not hasattr(self, 'ignore_query_truncation'):
            # WHAT THE HECK?!?!  WARN THE USER: BLAST RESULTS ARE SCREWY...
            raise ValueError(
                """BLAST appears to have truncated the Query: sequence
                to be shorter than the Sbjct: sequence:
                Query: %s
                Sbjct: %s
                This should not happen!  To ignore this error, please
                create an attribute ignore_query_truncation on the
                BlastHitParser object.""" % (self.query_seq, self.subject_seq))

    def get_interval_obj(self, q_start, q_end, s_start, s_end,
                         query_ori, query_factor, subject_ori, subject_factor):
        "return interval result as an object with attributes"
        o = BlastIval()
        o.hit_id = self.hit_id
        o.src_id = self.query_id
        o.dest_id = self.subject_id
        o.blast_score = self.blast_score
        o.e_value = self.e_value
        o.percent_id = self.identity_percent
        o.src_ori = query_ori
        o.dest_ori = subject_ori
        query_start = self.query_start+q_start*query_ori*query_factor
        query_end = self.query_start+q_end*query_ori*query_factor
        subject_start = self.subject_start+s_start*subject_ori*subject_factor
        subject_end = self.subject_start+s_end*subject_ori*subject_factor
        if query_start<query_end:
            o.src_start = query_start
            o.src_end = query_end
        else:
            o.src_start = query_end
            o.src_end = query_start
        if subject_start<subject_end:
            o.dest_start = subject_start
            o.dest_end = subject_end
        else:
            o.dest_start = subject_end
            o.dest_end = subject_start
        return o

    def is_valid_hit(self):
        return self.query_seq and self.subject_seq

    def generate_intervals(self):
        "generate interval tuples for the current alignment"
        yield CoordsGroupStart() # bracket with grouping markers

        query_ori, query_factor = get_ori_letterunit(self.query_start,\
                  self.query_end, self.query_seq, self.gapchar)
        subject_ori, subject_factor = get_ori_letterunit(self.subject_start,\
                  self.subject_end, self.subject_seq, self.gapchar)
        q_start= -1
        s_start= -1
        i_query=0
        i_subject=0
        for i in range(len(self.query_seq)): # SCAN ALIGNMENT FOR GAPS
            if self.query_seq[i] == self.gapchar or \
               self.subject_seq[i] == self.gapchar:
                if q_start >= 0: # END OF AN UNGAPPED INTERVAL
                    yield self.get_interval_obj(q_start, i_query,
                                                s_start, i_subject,
                                                query_ori, query_factor,
                                                subject_ori, subject_factor)
                q_start= -1
            elif q_start<0: # START OF AN UNGAPPED INTERVAL
                q_start=i_query
                s_start=i_subject
            if self.query_seq[i]!=self.gapchar: # COUNT QUERY LETTERS
                i_query+=1
            if self.subject_seq[i]!=self.gapchar: # COUNT SUBJECT LETTERS
                i_subject+=1
        if q_start>=0: # REPORT THE LAST INTERVAL
            yield self.get_interval_obj(q_start, i_query,
                                        s_start, i_subject,
                                        query_ori, query_factor,
                                        subject_ori, subject_factor)

        yield CoordsGroupEnd()

    def parse_file(self, myfile):
        "generate interval tuples by parsing BLAST output from myfile"
        for line in myfile:
            self.nline += 1
            if self.is_valid_hit() and \
               (is_line_start('>', line) or is_line_start(' Score =', line) \
                or is_line_start('  Database:', line) \
                or is_line_start('Query=', line)):
                for t in self.generate_intervals(): # REPORT THIS ALIGNMENT
                    yield t # GENERATE ALL ITS INTERVAL MATCHES
                self.reset() # RESET TO START A NEW ALIGNMENT
            if is_line_start('Query=', line):
                self.save_query(line)
            elif is_line_start('>', line):
                self.save_subject(line)
            elif is_line_start(' Score =', line):
                self.save_score(line)
            elif 'Identities =' in line:
                self.save_identity(line)
            elif is_line_start('Query:', line):
                self.save_query_line(line)
            elif is_line_start('Sbjct:', line):
                self.save_subject_line(line)
        if self.nline == 0: # no blast output??
            raise IOError('No BLAST output. Check that blastall is \
                          in your PATH')

if __name__=='__main__':
    import sys
    p=BlastHitParser()
    for t in p.parse_file(sys.stdin):
        print t
