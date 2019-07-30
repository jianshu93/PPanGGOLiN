#!/usr/bin/env python3
#coding: utf8

#default libraries
from collections import defaultdict

#local libraries
from ppanggolin.genome import Organism, Gene

class Edge:
    def __init__(self, sourceGene, targetGene, org):
        self.source = sourceGene.family
        self.target = targetGene.family
        self.source._edges[self.target] = self
        self.target._edges[self.source] = self
        self.organisms = defaultdict(list)
        self.addGenes(sourceGene, targetGene, org)

    def addGenes(self, sourceGene, targetGene, org):
        self.organisms[org].append((sourceGene, targetGene))

    def remove(self):
        self.source._edges[self.target].discard(self)
        self.target._edges[self.source].discard(self)

class GeneFamily:
    def __init__(self, ID, name):
        self.name = name
        self.ID = ID
        self._edges = {}
        self.genes = set()
        self.removed = False#for the repeated family not added in the main graph
        self.sequence = ""

    def addSequence(self, seq):
        self.sequence = seq

    def __str__(self):
        return str(self.ID)

    def addGene(self, gene):
        if not isinstance(gene, Gene):
            raise TypeError(f"'Gene' type object was expected, but '{type(gene)}' type object was provided.")
        self.genes.add(gene)

    @property
    def neighbors(self):
        return set(self._edges.keys())

    @property
    def edges(self):
        return set(self._edges.values())

    @property
    def organisms(self):
        return { gene.organism for gene in self.genes }

class Pangenome:
    def __init__(self):
        #basic parameters
        self._famGetter = {}
        self.max_fam_id = 0
        self.max_org_id = 0
        self._orgGetter = {}
        self._edgeGetter = {}
        self.status = {
                    'genomesAnnotated': "No",
                    'geneSequences' : "No",
                    'genesClustered':  "No",
                    'defragmented':"No",
                    'geneFamilySequences':"No",
                    'NeighborsGraph':  "No",
                    'Partitionned':  "No"
                }

    def addFile(self, pangenomeFile):
        from ppanggolin.formats import getStatus#importing on call instead of importing on top to avoid cross-reference problems.
        getStatus(self, pangenomeFile)
        self.file = pangenomeFile

    @property
    def genes(self):
        if len(self.organisms) > 0:#if we have organisms, they're supposed to have genes
            return [ gene for org in self._orgGetter.values() for contig in org.contigs for gene in contig.genes ]
        elif len(self.geneFamilies) > 0:#else, the genes will be stored in the gene families (maybe)
            return [ gene for geneFam in self.geneFamilies for gene in geneFam.genes ]

    @property
    def geneFamilies(self):
        return set(self._famGetter.values())

    @property
    def edges(self):
        return set(self._edgeGetter.values())

    @property
    def organisms(self):
        return set(self._orgGetter.values())

    def _yield_genes(self):
        """
            Use a generator to get all the genes of a pangenome
        """
        if len(self.organisms) > 0:#if we have organisms, they're supposed to have genes
            for org in self._orgGetter.values():
                for contig in org.contigs:
                     for gene in contig.genes:
                         yield gene
        elif len(self.geneFamilies) > 0:
            for geneFam in self.geneFamilies:
                for gene in geneFam.genes:
                    yield gene

    def _mkgeneGetter(self):
        """
            Since the genes are never explicitely 'added' to a pangenome (but rather to a gene family, or a contig), the pangenome cannot directly extract a gene from a geneID since it does not 'know' them.
            if at some point we want to extract genes from a pangenome we'll create a geneGetter.
            The assumption behind this is that the pangenome has been filled and no more gene will be added.
        """
        self._geneGetter = {}
        for gene in self._yield_genes():
            self._geneGetter[gene.ID] = gene

    def getGene(self, geneID):
        try:
            return self._geneGetter[geneID]
        except AttributeError:#in that case the gene getter has not been computed
            self._mkgeneGetter()#make it
            return self._geneGetter[geneID]#return what was expected.

    def __len__(self):
        return len(self.geneFamilies)

    def number_of_fams(self):
        return len(self.geneFamilies)

    def addPangenome(self, pangenome):
        """
            Will add informations from another pangenome to this pangenome.
            The assumption is that, if there are organism in common and contigs in common, the genes from the provided pangenome will be insered in the current pangenome at their position in the contig whether they existed previously or not.
        """
        for otherOrganism in pangenome.organism:
            org = self.getOrganism(otherOrganism.name)
            for otherContig in otherOrganism.contigs:
                contig = org.addContig(otherContig.name, otherContig.is_circular)
                for gene in otherContig.genes:
                    contig.addGene(gene)
                for rna in otherContig.RNA:
                    contig.addRNA(rna)

    def __iter__(self):
        return iter(self.geneFamilies)

    def info(self):
        infostr = ""
        infostr += f"Gene families : {len(self.geneFamilies)}\n"
        infostr += f"Organisms : {len(self.organisms)}\n"
        nbContig = 0
        for org in self.organisms:
            for _ in org.contigs:
                nbContig+=1
        infostr += f"Contigs : {nbContig}\n"
        infostr += f"Genes : {len(self.genes)}\n"
        infostr += f"Edges : {len(self.edges)}\n"
        return infostr

    def subgraph(self, famSet):
        ##currently, IDs will be different.
        g = Pangenome()
        # creating new fams from the old ones.
        famIds = {g.addGeneFamily(fam.name).ID for fam in famSet}
        for famID in famIds:
            # extracting the neighbors of each fam that still exists in the subgraph
            SubgraphNeighbors = {
                neighbor.ID for neighbor in self._famGetter[famID].neighbors if neighbor.ID in famIds}
            # setting the neighbors of each fam.
            g._famGetter[famID].neighbors = {
                g._famGetter[neighborId] for neighborId in SubgraphNeighbors}
        return g

    def getOrganism(self, name):
        """ returns an existing organism or adds a new one with the given name"""
        org = self._orgGetter.get(name)
        if org is None:
            org = Organism(name)
            self.addOrganism(org)
        return org

    def addOrganism(self, newOrg):
        """ adds an organism that did not exist previously in the pangenome"""
        oldLen = len(self._orgGetter)
        self._orgGetter[newOrg.name] = newOrg
        if len(self._orgGetter) == oldLen:
            raise KeyError(f"Redondant organism name was found ({newOrg.name}). All of your organisms must have unique names.")
        return newOrg

    def addGeneFamily(self, name):
        """
            Creates a geneFamily object with the provided name and adds it to the pangenome if it does not exist.
            Otherwise, does not create anything.
            returns the geneFamily object.
        """
        fam = self._famGetter.get(name)
        if fam is None:
            fam = self._createGeneFamily(name)
        return fam

    def addEdge(self, gene1, gene2, org):
        key = frozenset([gene1.family,gene2.family])
        edge = self._edgeGetter.get(key)
        if edge is None:
            edge = Edge(gene1, gene2, org)
            self._edgeGetter[key] = edge
        else:
            edge.addGenes(gene1,gene2,org)
        return edge

    def _createGeneFamily(self, name):
        newFam = GeneFamily(ID = self.max_fam_id, name = name)
        self.max_fam_id+=1
        self._famGetter[newFam.name] = newFam
        return newFam

    def removeFamsFrom(self, fams):
        oldSize = len(self._famGetter)
        for fam in fams:
            for edge in fams:
                edge.remove()
            del self._famGetter[fam.name]
            fam.removed = True
        if len(self._famGetter) + len(fams) != oldSize:
            raise Exception("Problems in the family removal from the pangenome.")

    def connectedComponents(self):
        """
            Yields subgraphs of each connected component.
        """
        seen = set()
        for v in self.geneFamilies:
            if v not in seen:
                c = set(self._plain_bfs(v))
                yield self.subgraph(c)
                seen.update(c)

    def _plain_bfs(self, source):
        """A fast BFS fam generator, copied and adapted from networkx"""
        seen = set()
        nextlevel = {source}
        while nextlevel:
            thislevel = nextlevel
            nextlevel = set()
            for v in thislevel:
                if v not in seen:
                    yield v
                    seen.add(v)
                    nextlevel.update(v.neighbors)

    def findCliques(self, fams=set()):
        """
            copied and adapted from networkx.
        """
        if len(fams) == 0:  # if no fams are given, we use the whole graph, else we start only from the given list of fams.
            fams = self.geneFamilies
        if len(fams) == 0:
            return
        Q = [None]

        subg = set(fams)
        cand = set(fams)
        # could be just u.neighbors if it's just on all the graph's fams.
        u = max(subg, key=lambda u: len(cand & u.neighbors))
        ext_u = cand - u.neighbors
        stack = []

        try:
            while True:
                if ext_u:
                    q = ext_u.pop()
                    cand.remove(q)
                    Q[-1] = q
                    adj_q = q.neighbors
                    subg_q = subg & adj_q
                    if not subg_q:
                        yield Q[:]
                    else:
                        cand_q = cand & adj_q
                        if cand_q:
                            stack.append((subg, cand, ext_u))
                            Q.append(None)
                            subg = subg_q
                            cand = cand_q
                            u = max(subg, key=lambda u: len(
                                cand & u.neighbors))
                            ext_u = cand - u.neighbors
                else:
                    Q.pop()
                    subg, cand, ext_u = stack.pop()
        except IndexError:
            pass