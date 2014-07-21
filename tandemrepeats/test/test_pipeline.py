import logging
import os
import pytest

from tandemrepeats.sequence import repeat_detection_run, sequence
from tandemrepeats.hmm import hmm

TEST_FAA_FILE_MBE_2014 = "P51610.fasta"
TEST_HMM_FILES_MBE_2014 = ["Kelch_1.hmm", "Kelch_2.hmm"]
TEST_SCORE_MBE_2014 = "phylo_gap01_ignore_trailing_gaps_and_coherent_deletions"

# TEST RESULT MBE 2014
# all[all$Ensembl_Protein_ID == 'ENSP00000309555',]
# TR_ID lHMM lRepeat_Region lRepeat_Region_Mean lRepeat_Region_Max lMean  n        nD detection_ID
# 19571_1   47            306           257.00353                364  50.0  5  4.061224      PF01344
# 19571_0   49            313           274.15901                354  48.8  6  5.265306      PF07646
# 19571_3   28            426            69.73498                530  29.0 14 13.275862      xstream
# 19571_2   28            429            69.02473                533  28.0 14 13.500000      xstream


TEST_FAA_FILE = "HIV-1_388796.faa"
TEST_HMM_FILE = "zf-CCHC.hmm"
TEST_DENOVO_PARAMETERS = {"detection": {"lFinders": ["XSTREAM", "TREKS"]}}
TEST_SCORE = "phylo_gap01"
TEST_RESULT_SEQ1 = [3, [["LFNSTKLE","LFNSST-N"], ["GDII", "GDIR"], ["FLG","FLG"]], 3,
         [["FNCGG-EF","FYCNTSNL","FNSTKLEL","FNSST-NL"], ["GDII", "GDIR"], ["FLG","FLG"]]]

notfixed = pytest.mark.notfixed

@pytest.fixture
def path():
    """Return the path to the test data files.
    """
    return os.path.join(os.path.abspath('.'), 'test')

def test_MBE_2014_pipeline():
    # The Schaper et al. (MBE, 2014) pipeline is tested on a single sequence.

    test_lSeq = sequence.Sequence.read(os.path.join(path(), TEST_FAA_FILE_MBE_2014))
    test_seq = test_lSeq[0]

    # Information on sequence domains (here: Pfam) in this sequence are added.
    test_pfam_hmm = [hmm.HMM.create( hmmer_file = os.path.join(path(),i) ) for i in TEST_HMM_FILES_MBE_2014]

    # The sequence is searched for tandem repetitions of the Pfam domain in the sequence
    test_pfam_list = test_seq.detect(lHMM = test_pfam_hmm)
    assert len(test_pfam_list.repeats) == 2

    # Pfam TRs with nD < 3.5 are discarded.
    test_pfam_list = test_pfam_list.filter("attribute", "nD", "min", 3.5)
    assert len(test_pfam_list.repeats) == 2

    # de novo detection methods (Trust, T-reks, Xstream, HHrepID) are used to search the
    test_denovo_list = test_seq.detect(denovo = True, **TEST_DENOVO_PARAMETERS)
    # When Trust is part of the detectors, the number of found repeats may differ between runs...
    assert len(test_denovo_list.repeats) == 10

    # De novo TRs with dTR_units (divergence) > 0.8; nD < 2.5; l < 10 or
    # pValue "phylo_gap01_ignore_trailing_gaps_and_coherent_deletions" > 0.01 are discarded.
    test_denovo_list = test_denovo_list.filter("pValue", TEST_SCORE_MBE_2014, 0.01)
    assert len(test_denovo_list.repeats) == 10
    test_denovo_list = test_denovo_list.filter("divergence", TEST_SCORE_MBE_2014, 0.8)
    assert len(test_denovo_list.repeats) == 10
    test_denovo_list = test_denovo_list.filter("attribute", "nD", "min", 2.5)
    assert len(test_denovo_list.repeats) == 5
    test_denovo_list = test_denovo_list.filter("attribute", "l", "min", 10)
    assert len(test_denovo_list.repeats) == 2

    # De novo TRs were remastered with HMM
    test_denovo_hmm = [hmm.HMM.create(repeat = iTR) for iTR in test_denovo_list.repeats]
    test_denovo_list_remastered = test_seq.detect(lHMM = test_denovo_hmm)
    assert len(test_denovo_list_remastered.repeats) == 2

    # pValue "phylo_gap01_ignore_trailing_gaps_and_coherent_deletions" > 0.1 are discarded.
    test_denovo_list_remastered = test_denovo_list_remastered.filter("pValue", TEST_SCORE_MBE_2014, 0.1)

    # De novo TRs were filtered (nD < 3.5 are discarded.)
    test_denovo_list_remastered = test_denovo_list_remastered.filter("attribute", "nD", "min", 3.5)
    assert len(test_denovo_list_remastered.repeats) == 2

    # De novo TRs overlapping with a Pfam TR were filtered
    test_denovo_list_remastered = test_denovo_list_remastered.filter("none_overlapping_fixed_repeats", test_pfam_list, "shared_char")
    assert len(test_denovo_list_remastered.repeats) == 2

    # Remaining De novo TRs were clustered for overlap (common ancestry). Only best =
    # lowest p-Value and lowest divergence were retained.
    test_denovo_list_remastered = test_denovo_list_remastered.filter("none_overlapping", ["common_ancestry"], {"pValue":TEST_SCORE_MBE_2014, "divergence":TEST_SCORE_MBE_2014})
    assert len(test_denovo_list_remastered.repeats) == 1

    # Merge remaining set of de novo and Pfam TRs.
    test_entire_set  = test_pfam_list + test_denovo_list_remastered
    assert len(test_entire_set.repeats) == 3

    # Write result set of Pfam TRs
    #test_entire_set.write(format = "xml,json,csv,...")


@notfixed
def test_pipeline():

    test_lSeq = sequence.Sequence.read(os.path.join(path(), TEST_FAA_FILE))

    for i,iSeq in enumerate(test_lSeq[:2]):
        test_repeat_denovo = iSeq.detect(denovo = True, **TEST_DENOVO_PARAMETERS)
        test_repeat_denovo_filtered = test_repeat_denovo.filter("pValue", TEST_SCORE, 0.05)
        test_repeat_denovo_hmm = [hmm.HMM.create(repeat = iTR) for iTR in test_repeat_denovo_filtered.repeats]
        test_repeat_denovo_remastered = iSeq.detect(lHMM = test_repeat_denovo_hmm)
        if i == 0:
            assert TEST_RESULT_SEQ1[0] == len(test_repeat_denovo.repeats)
            for k,l in zip(TEST_RESULT_SEQ1[1], test_repeat_denovo.repeats):
                assert k == l.msa
            assert TEST_RESULT_SEQ1[2] == len(test_repeat_denovo_filtered.repeats)
            for k,l in zip(TEST_RESULT_SEQ1[3], test_repeat_denovo_remastered.repeats):
                assert k == l.msa
            # CURRENTLY, ONLY THE FIRST SEQ IS TESTED.
            break