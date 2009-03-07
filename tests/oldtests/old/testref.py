from pygr.apps.seqref import *

def runTest():
    """Tests for ReferenceSequence and UnkSequence classes """
    ref=ReferenceSequence('AAACCCGGGTTTTGCAT','seq1')
    s=UnkSequence('seq1')
    ivals=(s[9],
           s[0:4],
           s[-4:-19],
           s[-19:-4],
           s[-100],
           s[-10:-15:3],
           s[-15:-10:3],
           s[10:15:3],
           s[15:10:3])
    
    m=ref.mapCoordinates(ivals)
    
    print ref
    
    for i in ivals:
        print repr(i),ref[i],repr(ref[i])

if __name__ == "__main__":
    runTest()
