#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File        : BtIO.py
Version     : 0.1
Author      : Dominik R. Laetsch, dominik.laetsch at gmail dot com 
Bugs        : ?
To do       : ?
"""

from __future__ import division
import re
import subprocess
import commands
from os.path import basename, isfile, abspath
import os
import lib.BtLog as BtLog

def parseList(infile):
    with open(infile) as fh:
        seqs = []
        for l in fh:
            seqs.append(l.rstrip("\n"))
    return seqs

def readFasta(infile):
    with open(infile) as fh: 
        header, seqs = '', []
        for l in fh: 
            if l[0] == '>':
                if (header):
                    yield header, ''.join(seqs)
                header, seqs = l[1:-1], []
            else:
                seqs.append(l[:-1])
        yield header, ''.join(seqs)

def runCmd(command):
    cmd = command.split() # sanitation
    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    return iter(p.stdout.readline, b'')

def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def checkBam(infile):
    if not (is_exe(samtools)):
        BtLog.error('7')
    mapped_reads_re = re.compile(r"(\d+)\s\+\s\d+\smapped")
    total_reads_re = re.compile(r"(\d+)\s\+\s\d+\sin total")
    total_reads, mapped_reads = 0, 0
    output = ''
    command = "samtools flagstat " + infile
    for line in runCmd(command):
        output += line
    mapped_reads = mapped_reads_re.search(output).group(1)
    total_reads = total_reads_re.search(output).group(1)
    return total_reads, mapped_reads

def readSam(infile, set_of_blobs):
    base_cov_dict = {}
    cigar_match_re = re.compile(r"(\d+)M") # only gets digits before M's
    total_reads = 0
    mapped_reads = 0
    with open(infile) as fh:
        for line in fh:
            match = line.split("\t")
            if match >= 11:
                total_reads += 1
                contig_name = match[2]
                if not contig_name == '*':  
                    if contig_name not in set_of_blobs:
                        error(errorMessage['4'] % (contig_name, infile))
                    base_cov = sum([int(matching) for matching in cigar_match_re.findall(match[5])])
                    if (base_cov):
                        mapped_reads += 1
                        base_cov_dict[contig_name] = base_cov_dict.get(contig_name, 0) + base_cov 
                        read_cov_dict[contig_name] = read_cov_dict.get(contig_name, 0) + 1 
    return base_cov_dict, total_reads, mapped_reads, read_cov_dict        

def readBam(infile, set_of_blobs):
    total_reads, mapped_reads = checkBam(infile)
    progress_unit = int(int(total_reads)/1000)
    base_cov_dict = {}
    read_cov_dict = {}
    cigar_match_re = re.compile(r"(\d+)M") # only gets digits before M's
    # execute samtools to get only mapped reads
    command = "samtools view -F 4 " + infile
    # only one counter since only yields mapped reads
    parsed_reads = 0 
    for line in runCmd(command):
        match = line.split("\t")
        if match >= 11:
            contig_name = match[2]
            base_cov = sum([int(matching) for matching in cigar_match_re.findall(match[5])])
            if (base_cov):
                parsed_reads += 1
                if contig_name not in set_of_blobs:
                    error('3', contig_name, infile)
                else:
                    base_cov_dict[contig_name] = base_cov_dict.get(contig_name, 0) + base_cov 
                    read_cov_dict[contig_name] = read_cov_dict.get(contig_name, 0) + 1 
        BtLog.progress(parsed_reads, progress_unit, total_reads)
    BtLog.progress(total_reads, progress_unit, total_reads)
    if not int(mapped_reads) == int(parsed_reads):
        print "mapped_reads != parsed_reads", mapped_reads, parsed_reads
    return base_cov_dict, total_reads, parsed_reads, read_cov_dict

def parseCovFromHeader(fasta_type, header ):
    ''' 
    Returns the coverage from the header of a FASTA 
    sequence depending on the assembly type
    '''
    if fasta_type == 'spades':
        return float(header.split("_")[-3])
    elif fasta_type == 'velvet':
        return float(header.split("_")[-1])
    elif fasta_type == 'abyss':
        temp = header.split(" ")
        return float(temp[2]/(temp[1]+1-75))
    else:
        pass

def readCov(infile, set_of_blobs):
    cov_line_re = re.compile(r"^(\S+)\t(\d+\.\d+)")
    i = 0
    with open(infile) as fh:
        for line in fh:
            i += 1
            BtLog.progress(i, 10, len(set_of_blobs))
            match = cov_line_re.search(line)
            if match:
                name, cov = match.group(1), float(match.group(2))
                if name not in set_of_blobs:
                    BtLog.error('3', name, infile)
                yield name, cov

def readCas(infile, order_of_blobs):
    cas_line_re = re.compile(r"\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+.\d{2})\s+(\d+)\s+(\d+.\d{2})")
    output = ''
    if not (is_exe('clc_mapping_info')):
        BtLog.error('20')
    else:
        command = "clc_mapping_info -s -f " + infile
        if (runCmd(command)):
            for line in runCmd(command):
                match = cas_line_re.search(line)
                if match:
                    idx = int(match.group(1)) - 1 # -1 because index of contig list starts with zero 
                    name = order_of_blobs[idx]
                    cov = float(match.group(4))
                    yield name, cov
    #error_CAS, message = commands.getstatusoutput("clc_mapping_info -s -f " + infile)
    #if (error_CAS):
    #    sys.exit("[ERROR] - Please add clc_mapping_info to you PATH variable.") 
    #command = "clc_mapping_info -n " + infile
    #cas_line_re = re.compile(r"\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+.\d{2})\s+(\d+)\s+(\d+.\d{2})")
    #for line in runCmd(command):
    #    match = cas_line_re.search(line)
    #    if match:
    #        contig_index = int(match.group(1)) - 1 # -1 because index of contig list starts with zero 
    #        contig_id = self.index[contig_index]
    #        contig_cov = float(match.group(4))
    #        yield contig_id, contig_cov

def readTax(infile, set_of_blobs):
    '''
    If more fields need to be parsed:
        - change hit_line_re
        - catch matches in variables
        - add as key-value pairs to hitDict
    '''
    hit_line_re = re.compile(r"^(\S+)\s+(\d+)\s+(\d+\.*\d*)")
    with open(infile) as fh:
        for line in fh:
            match = hit_line_re.search(line)
            if match:
                hitDict = {
                    'name' : match.group(1),
                    'taxId' : match.group(2), # string because if int, conversion is a nightmare ...
                    'score' : float(match.group(3))
                    }
                if hitDict['name'] not in set_of_blobs:
                    BtLog.error('19', hitDict['name'], infile)
                yield hitDict



def getNodesDB(**kwargs):
    '''
    Parsing names.dmp and nodes.dmp into the 'nodes_db' dict of dicts that 
    gets JSON'ed into blobtools/data/nodes_db.json if this file 
    does not exist. This file is used if neither "--names" and "--nodes" 
    nor "--db" is specified.
    '''
    nodesDB = {}
    nodesDB_f = ''    
    if (kwargs['names'] and kwargs['nodes']):
        print BtLog.status_d['3'] % (kwargs['nodes'], kwargs['names'])
        nodesDB = {}
        nodes_count = 0
        with open(kwargs['nodes']) as fh:
            for line in fh:
                nodes_col = line.split("\t")
                node = {}
                node_id = nodes_col[0] 
                node['parent'] = nodes_col[2]
                node['rank'] = nodes_col[4]
                nodesDB[node_id] = node
                nodes_count += 1
        with open(kwargs['names']) as fh:
            for line in fh:
                names_col = line.split("\t")
                if names_col[6] == "scientific name":
                   nodesDB[names_col[0]]['name'] = names_col[2]
        nodesDB_f = kwargs['nodesDB']
        nodesDB['nodes_count'] = nodes_count
    elif(kwargs['nodesDB']):
        print BtLog.status_d['4'] % (kwargs['nodesDB'])
        nodesDB = readNodesDB(kwargs['nodesDB'])
        nodesDB_f = kwargs['nodesDB']
    else:
        BtLog.error('3')
    return nodesDB, nodesDB_f

def readNodesDB(nodesDB_f):
    nodesDB = {}
    nodes_count = 0
    i = 0
    with open(nodesDB_f) as fh:
        for line in fh:
            if line.startswith("#"):
                nodes_count = int(line.lstrip("# nodes_count = ").rstrip("\n"))
            else:
                i += 1
                node, rank, name, parent = line.rstrip("\n").split("\t")
                nodesDB[node] = {'rank' : rank, 'name' : name, 'parent' : parent}
                BtLog.progress(i, 1000, nodes_count)
    return nodesDB

def writeNodesDB(nodesDB, nodesDB_f):
    nodes_count = nodesDB['nodes_count']
    i = 0
    with open(nodesDB_f, 'w') as fh:
        fh.write("# nodes_count = %s\n" % nodes_count) 
        for node in nodesDB:
            if not node == "nodes_count": 
                i += 1
                BtLog.progress(i, 1000, nodes_count)
                fh.write("%s\t%s\t%s\t%s\n" % (node, nodesDB[node]['rank'], nodesDB[node]['name'], nodesDB[node]['parent']))

def byteify(input):
    '''
    http://stackoverflow.com/a/13105359
    '''
    if isinstance(input, dict):
        return {byteify(key):byteify(value) for key,value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def writeJsonGzip(obj, outfile):
    import json
    import gzip
    with gzip.open(outfile, 'wb') as fh:    
        json.dump(obj, fh)

def writeJson(obj, outfile):
    import json
    with open(outfile, 'w') as fh:    
        json.dump(obj, fh)

def readJsonGzip(infile):
    import json
    import gzip
    with gzip.open(infile, 'rb') as fh:    
        obj = json.loads(fh.read().decode("ascii"))
    return byteify(obj)

def readJson(infile):
    import json
    with open(infile, 'r') as fh:    
        obj = json.loads(fh.read().decode("ascii"))
    return byteify(obj)

if __name__ == "__main__": 
    pass