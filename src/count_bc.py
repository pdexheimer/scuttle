import Levenshtein
import sys
import numpy as np
import scipy

class TagCorpus:
    def __init__(self, filename):
        #self._ids = []
        self._seqs = []
        self._id_lookup = {}
        if filename != None:
            with open(filename, 'r') as f:
                for line in f:
                    bc_id, seq = line.rstrip().split('\t')
                    #self._ids.append(bc_id)
                    self._seqs.append(seq)
                    self._id_lookup[seq] = bc_id
        self._ngrams = np.zeros((len(self._seqs), 64), dtype=int)
        xlat = [ a + b + c for a in 'ACGT' for b in 'ACGT' for c in 'ACGT' ]
        self._xlat = { seq: idx for idx, seq in enumerate(xlat) }
        for i in range(self._ngrams.shape[0]):
            seq = self._seqs[i]
            for j in range(len(seq)-2):
                ng = seq[j:j+3]
                if ng in self._xlat:
                    self._ngrams[i,self._xlat[ng]] += 1
    
    def __contains__(self, item):
        return item in self._id_lookup

    def __getitem__(self, key):
        return self._id_lookup[key]
    
    def nearest_match(self, needle):
        ngram = np.zeros((1, 64), dtype=int)
        for i in range(len(needle)-2):
            ng = needle[i:i+3]
            if ng in self._xlat:
                ngram[0, self._xlat[ng]] += 1
        distances = scipy.spatial.distance.cdist(ngram, self._ngrams, 'cosine')
        return self._seqs[distances.argmax()]


class TagCorpusOld:
    def __init__(self, filename):
        self._id_lookup = {}
        self._by_prefix = { i: { j: {} for j in 'ACGTN' } for i in 'ACGTN' }
        if filename != None:
            with open(filename, 'r') as f:
                for line in f:
                    bc_id, seq = line.rstrip().split('\t')
                    self._id_lookup[seq] = bc_id
                    self._by_prefix[seq[0]][seq[1]][seq] = bc_id

    def __contains__(self, item):
        return item in self._id_lookup

    def __getitem__(self, key):
        return self._id_lookup[key]
    
    def items_with_prefix(self, prefix):
        return self._by_prefix[prefix[0]][prefix[1]].items()

    def items(self):
        return self._id_lookup.items()

def _load_tags(filename):
    if filename == None:
        return None
    tags = {}
    with open(filename, 'r') as f:
        for line in f:
            bc_id, seq = line.rstrip().split('\t')
            tags[seq] = bc_id
    return tags

def initialize_barcodes(bc14_filename, bc30_filename):
    global bc14_tags, bc30_tags
    #bc14_tags = _load_tags(bc14_filename)
    #bc30_tags = _load_tags(bc30_filename)
    bc14_tags = TagCorpus(bc14_filename)
    bc30_tags = TagCorpus(bc30_filename)

def _error_correct(sequence, tags):
    # No correction possible
    if tags == None:
        return sequence

    # Perfect match
    if sequence in tags:
        return tags[sequence]

    bestmatch = tags.nearest_match(sequence)
    if Levenshtein.hamming(sequence, bestmatch) < 3:
        return tags[bestmatch]

    # for expected_seq, name in tags.items_with_prefix(sequence[:2]):
    #     if Levenshtein.hamming(sequence, expected_seq) < 3:
    #         return name

    # # Error correct - it's faster to iterate through all possible tags and check the distance
    # # than it is to generate all possible variations of this sequence
    # for expected_seq, name in tags.items():
    #     if Levenshtein.hamming(sequence, expected_seq) < 3:
    #         return name
    
    # Error correct failed, no idea what this sequence should be
    return None

def count(barcodes):
    counts = {}
    for (cell, umi, fourteen, thirty) in barcodes:
        bc14_id = _error_correct(fourteen, bc14_tags)
        if bc14_id == None:
            continue
        bc30_id = _error_correct(thirty, bc30_tags)
        if bc30_id == None:
            continue
        bc = f"{bc14_id}:{bc30_id}"
        
        # Count reads for each cell/tag combination
        # If this should ever change to a count of UMIs, store the UMIs in a set and take the len at the end
        counts.setdefault(cell, {})
        counts[cell].setdefault(bc, 0)
        counts[cell][bc] += 1
    #print('*', end='', file=sys.stderr, flush=True)
    return counts