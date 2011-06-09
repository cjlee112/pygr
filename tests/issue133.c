
/* TO BUILD THIS TEST:
gcc -g -I../pygr -DBUILD_C_LIBRARY issue133.c ../pygr/intervaldb.c -o testme

 */

#define BUILD_C_LIBRARY
#include "intervaldb.h"
int main() {
	const int n = 4;
	IntervalMap im[n];
	unsigned i,j;
	int found;
	int ntop, nlists;
	IntervalIterator *it;

	for (i = 0; i < 4; ++i) {
		im[i].start = i;
		im[i].end = 2*(i+1);
		im[i].target_id = 0;
	}

	SublistHeader *subheader = build_nested_list_inplace(im, 4, &ntop, &nlists);

	IntervalIterator *ito = interval_iterator_alloc();

	IntervalMap buf[1];
	for (it = ito; it;) {
		find_intervals(it, 0, 8, im, n, subheader, nlists, buf, 1, &found, &it);
		for (j=0;j<found;j++)
			printf("Found overlap: %d %d\n", buf[j].start, buf[j].end);
	}

	free_interval_iterator(ito);
}
