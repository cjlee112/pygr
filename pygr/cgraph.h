
#include <stdlib.h>

typedef struct {
  int k;
  int v;
} CDictEntry;

typedef struct {
  int n;
  CDictEntry *dict;
} CDict;

typedef struct {
  int k;
  CDict *v;
} CGraphEntry;

typedef struct {
  int n;
  CGraphEntry *dict;
} CGraph;

extern CDict *cdict_alloc(int n);
extern int cdict_free(CDict *d);
extern CDictEntry *cdict_getitem(CDict *d,int k);
extern CGraph *cgraph_alloc(int n);
extern int cgraph_free(CGraph *d);
extern CGraphEntry *cgraph_getitem(CGraph *d,int k);

