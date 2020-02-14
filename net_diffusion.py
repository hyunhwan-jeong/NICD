import networkx as nx
import pandas as pd
import logging

class Solver:
    df = pd.read_table("data/PCNet_v1.3.tsv", sep = "\t")
    G = nx.from_pandas_edgelist(df, 'from', 'to')
    G.remove_node("UBC")
    snp2disease = pd.read_table("data/all_variant_disease_associations.tsv.gz", sep = "\t")
    snp2gene = pd.read_table("data/variant_to_gene_mappings.tsv.gz", sep = "\t")

    @staticmethod
    def get_neighbors(disease_id):
        snps = set(Solver.snp2disease[Solver.snp2disease.diseaseId==disease_id].snpId)
        genes = set(Solver.snp2gene[Solver.snp2gene['snpId'].isin(snps)].geneSymbol)
        edges = {}
        black_list = set()
        for n in genes:
            if not n in Solver.G.nodes: 
                black_list.add(n)
                continue
            for v in Solver.G.neighbors(n):
                if v in genes: continue
                if not v in edges: edges[v] = set()
                edges[v].add(n)

        return({
            'init' : genes - black_list,
            'neighbors': edges
        })
        

    @staticmethod
    def format_neighbors_object(obj_A, obj_B):

        all_intermed_genes = set(obj_A['neighbors'].keys()) | set(obj_B['neighbors'].keys())
        edges = [ \
            {'node' : v, 
            'a' : obj_A['neighbors'][v] - obj_B['init'] if v in obj_A['neighbors'] else set() , \
            'b' : obj_B['neighbors'][v] - obj_A['init'] if v in obj_B['neighbors'] else set() } for v in all_intermed_genes ]
        return sorted(edges, key = lambda v : -len(v['a']) * len(v['b']))

    @staticmethod
    def solve(obj_A, obj_B):
        ordered_intermed_genes = Solver.format_neighbors_object(obj_A, obj_B)
        remained_A, remained_B = A['init'] - B['init'], B['init'] - A['init']
        found = False
        solution = []
        solution_edges = { 'from' : [], 'to' : [] }

        for v in ordered_intermed_genes:
            if len(remained_A) == 0 and len(remained_B) == 0:
                found = True
                break

            if len(remained_A & v['a']) == 0 and len(remained_B & v['b']) == 0:
                continue

            solution.append(v['node'])

            remained_A -= v['a']
            remained_B -= v['b']

            for n in v['a'] | v['b']:
                solution_edges['from'].append(v['node'])
                solution_edges['to'].append(n)

        return {
            'node' : solution,
            'edges' : pd.DataFrame(solution_edges),
            'result' : found
        }


A = Solver.get_neighbors("C0520679")
B = Solver.get_neighbors("C0497327")
print(Solver.solve(A, B))


import numpy as np

W = np.array([ 1.0 if v in A['init'] else 0 for v in Solver.G.nodes ])
matrix = nx.convert_matrix.to_numpy_matrix(Solver.G)
lap_mat = np.matmul(matrix, np.diagflat(1/np.sum(matrix, axis=0)))

alpha = 0.5
niter = 10

W0 = np.matrix(W).T
W_t0 = np.matrix(W).T

lst_i, lst_diff = [], []
for i in range(niter):
    W_t1 = alpha * lap_mat * W_t0 + (1-alpha)*W0
    diff = np.linalg.norm(W_t1-W_t0)
    print(i, diff)
    lst_i.append(i)
    lst_diff.append(diff)
    W_t0 = W_t1
    if diff < 1e-6: break
