class MySliceInfo(object):

    def __init__(self, id, start, stop, orientation):
        self.id = id
        self.start = start
        self.stop = stop
        self.orientation = orientation


class MyFunkySliceInfo(object):

    def __init__(self, seq_id, begin, end, strand):
        self.seq_id = seq_id
        self.begin = begin
        self.end = end
        self.strand = strand
