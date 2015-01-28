"""This module is used for the storage analysis."""

from scipy.sparse import dia_matrix

import numpy as np
import collections
import math
from math import ceil

bits_per_double_data = 64
bytes_per_double_data = 8
bytes_per_metadata = 4


def coo(matrix):
    nnz = matrix.nnz
    return (2 * nnz * bytes_per_metadata,
            nnz * bytes_per_double_data,
            'COO')


def csc(matrix):
    nnz = matrix.nnz
    return ((len(matrix.indptr) + nnz) * bytes_per_metadata,
            nnz * bytes_per_double_data,
            'CSC')

def csr(matrix, mantissa_bitwidth = 52, index_bitwidth = 32):
    '''
       Compute storage size for CSR matrix with IEEE 745 values with 11 bit
       exponent (as for IEEE double) and custom bitwidth of mantissa.
    '''
    nnz = matrix.nnz
    # IEEE float bitwidth: mantissa_bitwidth + sign bit + 11 bit exponent,
    # assuming mantissa_bitwidth is a number of explicitly stored bits
    bits_per_custom_data = (mantissa_bitwidth + 12)
    metadata_bitsize = (len(matrix.indptr) + nnz) * index_bitwidth

    return (metadata_bitsize/8.0,
            (nnz * bits_per_custom_data)/8.0,
            "CSR: {:2d} bit data and ".format(bits_per_custom_data) +
            str(index_bitwidth) + " bit index")


def csr_buckets(n, nnz, num_buckets, fixed_point_bitwidth = 16, index_bitwidth = 32):
    '''
       Compute storage size for CSR matrix with bucket-based mixed precision
       IEEE 745 doubles + fixed_point correction terms of custom bitwidth
    '''
    # each bucket has one IEEE 745 double + custom bitwidth corrections
    # (for each entry, nnz in total)
    bits_per_custom_data = num_buckets*bits_per_double_data + nnz*fixed_point_bitwidth
    metadata_bitsize = (n + nnz) * index_bitwidth

    return (metadata_bitsize/8.0,
            (bits_per_custom_data)/8.0,
            "CSR: bucketing with {:2d} correction terms and ".format(fixed_point_bitwidth) +
            str(index_bitwidth) + " bit index")




def dia(matrix):
    dia_m = dia_matrix(matrix)
    nnz = dia_m.nnz
    return (bytes_per_metadata * len(dia_m.offsets),
            nnz * bytes_per_double_data,
            'DIA')


def bounded_dictionary(n, matrix_values,
                       decoding_table_bitwidth=None, counter=None):
    """Do a bounded dictionary compression of the given stream of values.
    This works by finding the k highest frequency elements and
    replacing their occurence with a pointer.

    If decoding_table_width is specified then k is 1 <<
    decoding_table_bitwidth. Otherwise k is the minimal number of bits
    to represent the unique values of the matrix =
    ceil(log(len(set(matrix_values)), 2).

    """
    if not counter:
        counter = collections.Counter()
        for v in matrix_values:
            counter[v] += 1

    nnzs = len(matrix_values)

    # assume all are covered if k is not specified
    covered = float(nnzs)
    bits_per_entry = decoding_table_bitwidth
    if not decoding_table_bitwidth:
        bits_per_entry = int(ceil(math.log(len(counter), 2)))
    k = 1 << bits_per_entry
    if k:
        covered = 0.0
        for v, c in counter.most_common(k):
            covered += c

    bytes_compressed_entries = ceil(covered * bits_per_entry / 8.0)
    bytes_uncompressed_entries = (nnzs - covered) * bytes_per_double_data
    bytes_overhead = n * bytes_per_metadata if k else 0

    return ceil(bytes_compressed_entries +
                bytes_uncompressed_entries +
                bytes_overhead), counter, covered


def csr_bounded_dictionary(matrix, dict_size=10):
    """Estimate the storage for the given matrix after
    we encode it as CSR and apply bounded dictionary
    encoding to the values stream"""
    nnz = matrix.nnz

    value_bytes = bounded_dictionary(matrix.data, dict_size)

    return ((len(matrix.indptr) + nnz) * bytes_per_metadata,
            value_bytes,
            'CSR_BD')
