# scuttle - manage and manipulate sc-rna data files
# Copyright (C) 2019 Phillip Dexheimer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import Levenshtein
import numpy as np
import scipy


class TagCorpus:
    def __init__(self, filename):
        self._seqs = []
        self._id_lookup = {}
        if filename is not None:
            with open(filename, 'r') as f:
                for line in f:
                    bc_id, seq = line.rstrip().split('\t')
                    self._seqs.append(seq)
                    self._id_lookup[seq] = bc_id
        self._ngrams = np.zeros((len(self._seqs), 64), dtype=int)
        xlat = [a + b + c for a in 'ACGT' for b in 'ACGT' for c in 'ACGT']
        self._xlat = {seq: idx for idx, seq in enumerate(xlat)}
        for i in range(self._ngrams.shape[0]):
            seq = self._seqs[i]
            for j in range(len(seq)-2):
                ng = seq[j:j+3]
                if ng in self._xlat:
                    self._ngrams[i, self._xlat[ng]] += 1

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


def initialize_barcodes(bc14_filename, bc30_filename):
    global bc14_tags, bc30_tags
    bc14_tags = TagCorpus(bc14_filename)
    bc30_tags = TagCorpus(bc30_filename)


def error_correct(sequence, tags):
    # Perfect match
    if sequence in tags:
        return tags[sequence]

    # Error correct - it's faster to iterate through all possible tags and check the distance
    # than it is to generate all possible variations of this sequence
    for expected_seq, name in tags.items():
        if Levenshtein.hamming(sequence, expected_seq) < 3:
            return name

    # Error correct failed, no idea what this sequence should be
    return None


def count(barcodes):
    counts = {}
    for (cell, _umi, fourteen, thirty) in barcodes:
        bc14_id = error_correct(fourteen, bc14_tags)
        if bc14_id is None:
            continue
        bc30_id = error_correct(thirty, bc30_tags)
        if bc30_id is None:
            continue
        bc = f'{bc14_id}:{bc30_id}'

        # Count reads for each cell/tag combination
        # If this should ever change to a count of UMIs, store the UMIs in a set and take the len at the end
        counts.setdefault(cell, {})
        counts[cell].setdefault(bc, 0)
        counts[cell][bc] += 1
    return counts
