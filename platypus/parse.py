#!/usr/bin/env python
# File created on 13 Jul 2013
from __future__ import division

__author__ = "Antonio Gonzalez Pena"
__copyright__ = "Copyright 2011-2013, The Platypus Project"
__credits__ = ["Antonio Gonzalez Pena"]
__license__ = "GPL"
__version__ = "0.0.8-dev"
__maintainer__ = "Antonio Gonzalez Pena"
__email__ = "antgonza@gmail.com"
__status__ = "Development"


from cogent.parse.blast import MinimalBlastParser9


def parse_first_database(db, percentage_ids, alignment_lengths):
    """ parses 1st db file and finds the seqs with hits above the given threshold

    inputs:
        db: file pointer to 1st database
        percentage_ids: array with percentage values
        alignment_lengths: array with alignment length values

    output:
        total_queries: total number of seqs in the db
        best_hits: dict of seqs and hits
            {'seq_id': 
                [{ 'a': { 'evalue':%f, 'percentageId':%f, 'bitScore':%f, 
                          'subjectId':%s, 'algLength':%f }, 
                          'evalue': float(h[evalue]) },
                   'b': { 'subject_id': None, 'bit_score': -1 }, 
                   # One element for each combination of %id and alignment length
                ]
            } 
    """
    #@@@ Try blast parser object
    results = MinimalBlastParser9(db)

    #@@@ cogent.util.transform.cartesian_product
    options = [(p,a) for p in percentage_ids for a in alignment_lengths]

    best_hits = {}
    for total_queries, (metadata, hits) in enumerate(results):
        fields = [i.strip() for i in metadata['FIELDS'].split(',')]
        name = metadata['QUERY']
        percentage_id = fields.index('% identity')
        bit_score = fields.index('bit score')
        alg_length = fields.index('alignment length')
        evalue = fields.index('e-value')
        subject_id = fields.index('Subject id')

        if not hits: 
            continue

        best_hits[name] = []
        for p,a in options:
            # best bit score
            bbs = 0
            result = None

            for h in hits:
                h[percentage_id] = float(h[percentage_id])
                h[alg_length] = float(h[alg_length])
                h[bit_score] = float(h[bit_score])

                if h[percentage_id]>=p and h[alg_length]>=a and h[bit_score]>bbs:
                    result =  { 'a': { 'subject_id': h[subject_id],
                                       'percentage_id': h[percentage_id],
                                       'bit_score': h[bit_score],
                                       'alg_length': int(h[alg_length]),
                                       'evalue': float(h[evalue]) },
                                'b': { 'subject_id': None, 
                                       'bit_score': -1 } }
                    bbs = h[bit_score]
            best_hits[name].append(result)

    return total_queries+1, best_hits


def parse_second_database(db, best_hits, percentage_ids_other,
                        alignment_lengths_other):
    """ parses 2nd database, only looks at successful hits of the 1st

    inputs:
        db: filename of the blast results against a database without first
        best_hits: a dict with the successful results from parse_first_database 
        percentage_ids: array with percentage values
        alignment_lengths: array with alignment length values

    output:
        None: the command modifies best_hits, section b
    """
    results = MinimalBlastParser9(db)

    #@@@ create function to return results
    for metadata, hits in results:
        fields = [i.strip() for i in metadata['FIELDS'].split(',')]
        name = metadata['QUERY']
        percentage_id = fields.index('% identity')
        bit_score = fields.index('bit score')
        alg_length = fields.index('alignment length')
        evalue = fields.index('e-value')
        subject_id = fields.index('Subject id')

        if name in best_hits:
            for i,(p,a) in enumerate([(p,a) for p in percentage_ids_other \
                                            for a in alignment_lengths_other]):
                if not best_hits[name][i]:
                    continue

                # best bit score
                bbs = 0
                result = None
                for h in hits:
                    h[percentage_id] = float(h[percentage_id])
                    h[alg_length] = float(h[alg_length])
                    h[bit_score] = float(h[bit_score])                                  
                    if h[percentage_id]>=p and h[alg_length]>=a and h[bit_score]>bbs:
                        result =  { 'subject_id': h[subject_id],
                                    'percentage_id': h[percentage_id],
                                    'bit_score': h[bit_score],
                                    'alg_length': int(h[alg_length]),
                                    'evalue': float(h[evalue]) }
                        bbs = h[bit_score]
                if result:
                    best_hits[name][i]['b'] = result


def process_results(percentage_ids, alignment_lengths, percentage_ids_other,
                    alignment_lengths_other, best_hits):
    """Writes the individual rarefaction levels and then returns the collated result

    inputs:

    output: 
    """

    len_percentage_ids = len(percentage_ids)
    len_alignment_lengths = len(alignment_lengths)
    results = []

    for i, j in [(i,j) for i in range(len_percentage_ids) for j in range(len_alignment_lengths)]:
        filename = "p1_%d-a1_%d_p2_%d-a2_%d" % (percentage_ids[i],
            alignment_lengths[j], percentage_ids_other[i], alignment_lengths_other[j])
        results.append({ 'filename': filename, 'db_interest': 0, 'db_other': 0,
            'perfect_interest': 0, 'equal': 0, 'summary': ['#SeqId\tFirst\t'
            'Second'], 'db_seqs_counts': {'a': {}, 'b': {} } })

    for seq_name, values in best_hits.items():
        seq_name = seq_name.split(' ')[0].strip()
        for i, vals in enumerate(values):
            if not vals:
                continue

            # Validating duplicated results in the databases
            #@@@ Do this step in a different script early in the pipeline
            if vals['a']['subject_id'] not in results[i]['db_seqs_counts']['a']:
                results[i]['db_seqs_counts']['a'][vals['a']['subject_id']]=0
                if vals['a']['subject_id'] == results[i]['db_seqs_counts']['b']:
                    raise Warning, "%s is in both databases" % vals['a']['subject_id']
            if vals['b']['subject_id'] not in results[i]['db_seqs_counts']['b']:
                results[i]['db_seqs_counts']['b'][vals['b']['subject_id']]=0
                if vals['b']['subject_id'] == results[i]['db_seqs_counts']['a']:
                    raise Warning, "%s is in both databases" % vals['b']['subject_id']

            # Comparing bit_scores to create outputs
            if vals['a']['bit_score']==vals['b']['bit_score']:
                results[i]['equal'] += 1
                results[i]['summary'].append('%s\t%s\t%s' % (seq_name, vals['a']['subject_id'], vals['b']['subject_id']))
                results[i]['db_seqs_counts']['a'][vals['a']['subject_id']] += 1
                results[i]['db_seqs_counts']['b'][vals['b']['subject_id']] += 1
            elif vals['a']['bit_score']>vals['b']['bit_score']:
                if not vals['b']['subject_id']:
                    results[i]['perfect_interest'] += 1 
                    results[i]['summary'].append('%s\t%s\t' % (seq_name, vals['a']['subject_id']))
                results[i]['db_seqs_counts']['a'][vals['a']['subject_id']] += 1
            else:
                results[i]['db_other'] += 1
                results[i]['summary'].append('%s\n\t%s' % (seq_name, ''))
                results[i]['db_seqs_counts']['b'][vals['b']['subject_id']] += 1

    return results
