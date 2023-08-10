#!/usr/bin/env python3
# coding: utf8

# default libraries
from __future__ import annotations
import logging
from collections.abc import Iterable

# installed libraries
from typing import Dict, Generator, List, Set

import gmpy2

# local libraries
from ppanggolin.genome import Gene, Organism, Contig, RNA
from ppanggolin.geneFamily import GeneFamily
from ppanggolin.metadata import MetaFeatures


class Region(MetaFeatures):
    """
    The 'Region' class represents a region of genomic plasticity.
    Methods:
        - 'genes': the property that generates the genes in the region as they are ordered in contigs.
        - 'families': the property that generates the gene families in the region.
        - 'Length': the property that gets the length of the region.
        - 'organism': the property that gets the organism linked to the region.
        - 'Contig': the property that gets the starter contig linked to the region.
        - 'is_whole_contig': the property that indicates if the region is an entire contig.
        - 'is_contig_border': the property that indicates if the region is bordering a contig.
        - 'get_rnas(self) -> set': the method that gets the RNA in the region.
        - 'get_bordering_genes(self, n: int, multigenics: set) -> list': the method that gets the bordered genes in the region.

    Fields:
        - 'name': the name of the region.
        - 'score': the score of the region.
        - 'Starter': the first gene in the region.
        - 'stopper': the last gene in the region.
    """

    def __init__(self, region_id: str):
        """Constructor method

        :param region_id: identifier of the region
        """
        super().__init__()
        self._genes_getter = {}
        self.name = region_id
        self.score = 0
        self.starter = None
        self.stopper = None

    def __repr__(self):
        return f"RGP name:{self.name}"

    def __hash__(self):
        return id(self)

    def __eq__(self, other: Region) -> bool:
        """
        Expects another Region type object. Will test whether two Region objects have the same gene families

        :param other: Other region to test equality of region

        :return: equal or not
        """
        if not isinstance(other, Region):
            raise TypeError(f"'Region' type object was expected, but '{type(other)}' type object was provided.")
        if [gene.family for gene in self.genes] == [gene.family for gene in other.genes]:
            return True
        if [gene.family for gene in self.genes] == [gene.family for gene in list(other.genes)[::-1]]:
            return True
        return False

    def __len__(self):
        return len(self._genes_getter)

    def __setitem__(self, position, gene):
        if not isinstance(gene, Gene):
            raise TypeError(f"Unexpected class / type for {type(gene)} "
                            f"when adding it to a region of genomic plasticity")
        if len(self) > 0:
            if gene.organism != self.organism:
                raise Exception(f"Gene {gene.name} is from a different organism than the first defined in RGP. "
                                f"That's not possible")
            if gene.contig != self.contig:
                raise Exception(f"Gene {gene.name} is from a different contig than the first defined in RGP. "
                                f"That's not possible")
        if position in self._genes_getter and self[position] != gene:
            raise ValueError("Another gene already exist at this position")
        self._genes_getter[position] = gene
        self.starter = self._genes_getter[min(self._genes_getter.keys())]
        self.stopper = self._genes_getter[max(self._genes_getter.keys())]
        gene.RGP = self

    def __getitem__(self, position):
        try:
            return self._genes_getter[position]
        except KeyError:
            raise KeyError(f"There is no gene at position {position} in RGP {self.name}")

    def __delitem__(self, position):
        del self._genes_getter[position]

    @property
    def genes(self) -> Generator[Gene, None, None]:
        """Generate the gene as they are ordered in contigs
        """
        for gene in sorted(self._genes_getter.values(), key=lambda x: x.position):
            yield gene

    @property
    def families(self) -> Generator[GeneFamily, None, None]:
        """Get the gene families in the RGP

        :return: Set of gene families
        """
        for gene in self.genes:
            yield gene.family

    def number_of_families(self) -> int:
        """Get the number of different gene families in the region
        """
        return len(set(self.families))

    @property
    def length(self):
        """Get the length of the region
        """
        return self.stopper.stop - self.starter.start

    @property
    def organism(self) -> Organism:
        """ Get the Organism link to RGP

        :return: Organism
        """
        return self.starter.organism

    @property
    def contig(self) -> Contig:
        """ Get the starter contig link to RGP

        :return: Contig
        """
        return self.starter.contig

    @property
    def is_whole_contig(self) -> bool:
        """Indicates if the region is an entire contig

        :return: True if whole contig
        """
        if self.starter.position == 0 and self.stopper.position == len(self.contig) - 1:
            return True
        return False

    @property
    def is_contig_border(self) -> bool:
        """Indicates if the region is bordering a contig

        :return: True if bordering
        """
        if len(self) == 0:
            raise Exception("Your region has no genes. Something wrong happenned.")
        min_pos = min(self.contig.genes, key=lambda x: x.position).position
        max_pos = max(self.contig.genes, key=lambda x: x.position).position
        if not self.contig.is_circular:
            if self.starter.position == min_pos or self.stopper.position == max_pos:
                return True
        return False

    def get_bordering_genes(self, n: int, multigenics: set) -> List[List[Gene], List[Gene]]:
        """ Get the bordered genes in the region

        :param n: number of genes to get
        :param multigenics: pangenome graph multigenic persistent families

        :return: A list of bordering gene in start and stop position
        """
        # TODO add Exception
        border = [[], []]
        pos = self.starter.position
        init = pos
        while len(border[0]) < n and (pos != 0 or self.contig.is_circular):
            curr_gene = None
            if pos == 0:  # TODO change for variable to be more flexible
                if self.contig.is_circular:
                    curr_gene = self.contig[pos - 1]
            else:
                curr_gene = self.contig[pos - 1]
            if curr_gene is not None and curr_gene.family not in multigenics and \
                    curr_gene.family.named_partition == "persistent":
                border[0].append(curr_gene)
            pos -= 1
            if pos == -1 and self.contig.is_circular:
                pos = len(self.contig)
            if pos == init:
                break  # looped around the contig
        pos = self.stopper.position
        init = pos
        while len(border[1]) < n and (pos != len(self.contig) - 1 or self.contig.is_circular):
            curr_gene = None
            if pos == len(self.contig) - 1:
                if self.contig.is_circular:
                    curr_gene = self.contig[0]
            else:
                curr_gene = self.contig[pos + 1]
            if curr_gene is not None and curr_gene.family not in multigenics:
                border[1].append(curr_gene)
            pos += 1
            if pos == len(self.contig) and self.contig.is_circular:
                pos = -1
            if pos == init:
                break  # looped around the contig
        return border


class Spot(MetaFeatures):
    """
    The 'Spot' class represents a region of genomic plasticity.
    Methods:
        - 'regions': the property that generates the regions in the spot.
        - 'families': the property that generates the gene families in the spot.
        - 'spot_2_families': add to Gene Families a link to spot.
        - 'borders': Extracts all the borders of all RGPs belonging to the spot
        - 'get_uniq_to_rgp': Get dictionnary with a representing RGP as key, and all identical RGPs as value
        - 'get_uniq_ordered_set': Get an Iterable of all the unique syntenies in the spot
        - 'get_uniq_content': Get an Iterable of all the unique rgp (in terms of gene family content) in the spot
        - 'count_uniq_content':  Get a counter of uniq RGP and number of identical RGP (in terms of gene family content)
        - 'count_uniq_ordered_set': Get a counter of uniq RGP and number of identical RGP (in terms of synteny content)

    Fields:
        - 'ID': Identifier of the spot
    """
    def __init__(self, spot_id: int):
        """Constructor method

        :param spot_id: identifier of the spot
        """
        if not isinstance(spot_id, int):
            raise TypeError(f"Spot identifier must be an integer. Given type is {type(spot_id)}")
        super().__init__()
        self.ID = spot_id
        self._region_getter = {}
        self._uniqOrderedSet = {}
        self._uniqContent = {}

    def __repr__(self):
        return f"Spot {self.ID} - #RGP: {len(self)}"

    def __str__(self):
        return f"spot_{self.ID}"

    def __setitem__(self, name, region):
        if not isinstance(region, Region):
            raise TypeError(f"A Region object is expected to be added to the spot. find type is {type(region)}")
        if name in self._region_getter and self[name] != region:
            raise KeyError("A Region with the same name already exist in spot")
        self._region_getter[name] = region

    def __getitem__(self, name):
        try:
            return self._region_getter[name]
        except KeyError:
            raise KeyError(f"Region with {name} does not exist in spot")

    def __delitem__(self, name):
        del self._region_getter[name]

    def __len__(self):
        return len(self._region_getter)

    @property
    def regions(self) -> Generator[Region, None, None]:
        """Generates the regions in the spot
        """
        for region in self._region_getter.values():
            yield region

    @property
    def families(self) -> Generator[GeneFamily, None, None]:
        """Get the gene families in the RGP
        """
        families = set()
        for region in self.regions:
            for family in region.families:
                if family not in families:
                    families.add(family)
                    yield family

    def number_of_families(self) -> int:
        """Return the number of different families in the spot
        """
        return len({family for region in self.regions for family in region.families})

    def spot_2_families(self):
        """Add to Gene Families a link to spot
        """
        for family in self.families:
            family.add_spot(self)

    def borders(self, set_size: int, multigenics) -> List[List[int, List[GeneFamily], List[GeneFamily]]]:
        """ Extracts all the borders of all RGPs belonging to the spot

        :param set_size: number of genes to get
        :param multigenics: pangenome graph multigenic persistent families

        :return: families that bordering spot
        """
        all_borders = []
        for rgp in self.regions:
            all_borders.append(rgp.get_bordering_genes(set_size, multigenics))

        family_borders = []
        for borders in all_borders:
            new = True
            curr_set = [[gene.family for gene in borders[0]], [gene.family for gene in borders[1]]]
            for i, (c, former_borders) in enumerate(family_borders):
                if former_borders == curr_set or former_borders == curr_set[::-1]:
                    family_borders[i][0] += 1
                    new = False
                    break
            if new:
                family_borders.append([1, curr_set])

        return family_borders

    def _mk_uniq_ordered_set_obj(self):
        """cluster RGP into groups that have an identical synteny"""
        for rgp in self.regions:
            z = True
            for seen_rgp in self._uniqOrderedSet:
                if rgp == seen_rgp:
                    z = False
                    self._uniqOrderedSet[seen_rgp].add(rgp)
            if z:
                self._uniqOrderedSet[rgp] = {rgp}

    def _get_ordered_set(self):
        """ Creates the _uniqSyn object if it was never computed. Return it in any case

        :return: RGP groups that have an identical synteny
        """
        if len(self._uniqOrderedSet) == 0:
            self._mk_uniq_ordered_set_obj()
        return self._uniqOrderedSet

    def get_uniq_to_rgp(self) -> Dict[Region, Set[Region]]:
        """ Get dictionnary with a representing RGP as key, and all identical RGPs as value

        :return: Dictionnary with a representing RGP as key, and set of identical RGPs as value
        """
        return self._get_ordered_set()

    def get_uniq_ordered_set(self) -> Set[Region]:
        """Get an Iterable of all the unique syntenies in the spot

        :return: Iterable of all the unique syntenies in the spot
        """
        return set(self._get_ordered_set().keys())

    def _mk_uniq_content(self):
        """cluster RGP into groups that have identical gene content"""
        for rgp in self.regions:
            z = True
            for seen_rgp in self._uniqContent:
                if rgp.families == seen_rgp.families:
                    z = False
                    self._uniqContent[seen_rgp].add(rgp)
            if z:
                self._uniqContent[rgp] = {rgp}

    def _get_content(self):
        """Creates the _uniqContent object if it was never computed.

        :return: RGP groups that have identical gene content
        """
        if len(self._uniqContent) == 0:
            self._mk_uniq_content()
        return self._uniqContent

    def get_uniq_content(self) -> Set[Region]:
        """ Get an Iterable of all the unique rgp (in terms of gene family content) in the spot

        :return: Iterable of all the unique rgp (in terms of gene family content) in the spot
        """
        return set(self._get_content().keys())

    def count_uniq_content(self) -> dict:
        """
        Get a counter of uniq RGP and number of identical RGP (in terms of gene family content)

        :return: dictionary with a representative rgp as key and number of identical rgp as value
        """
        return dict([(key, len(val)) for key, val in self._get_content().items()])

    def count_uniq_ordered_set(self):
        """
        Get a counter of uniq RGP and number of identical RGP (in terms of synteny content)

        :return: dictionary with a representative rgp as key and number of identical rgp as value
        """
        return dict([(key, len(val)) for key, val in self._get_ordered_set().items()])


class Module(MetaFeatures):
    """The `Module` class represents a module in a pangenome analysis.

    The `Module` class has the following attributes:
    - `ID`: An integer identifier for the module.
    - `bitarray`: A bitarray representing the presence/absence of the gene families in an organism.

    The `Module` class has the following methods:
    - `families`: Returns a generator that yields the gene families in the module.
    - `mk_bitarray`: Generates a bitarray representing the presence/absence of the gene families in an organism using the provided index.
    """
    def __init__(self, module_id: int, families: set = None):
        """Constructor method

        :param module_id: Module identifier
        :param families: Set of families which define the module
        """
        if not isinstance(module_id, int):
            raise TypeError(f"Module identifier must be an integer. Given type is {type(module_id)}")
        super().__init__()
        self.ID = module_id
        self._families_getter = {}
        if families is not None:
            for family in families:
                self[family.name] = family
        self.bitarray = None

    def __repr__(self):
        return f"Module {self.ID} - #Families: {len(self)}"

    def __str__(self):
        return f"module_{self.ID}"

    def __hash__(self):
        return id(self)

    def __len__(self):
        return len(self._families_getter)

    def __eq__(self, other: Module):
        if not isinstance(other, Module):
            raise TypeError(f"Another module is expected to be compared to the first one. You give a {type(other)}")
        if set(self.families) == set(other.families):
            return True
        else:
            return False

    def __setitem__(self, name, family):
        if not isinstance(family, GeneFamily):
            raise TypeError(f"A gene family is expected to be added to module. Given type was {type(family)}")
        if name in self._families_getter and self[name] != family:
            raise KeyError("A different gene family with the same name already exist in the module")
        self._families_getter[name] = family
        family.add_module(self)

    def __getitem__(self, name) -> GeneFamily:
        try:
            return self._families_getter[name]
        except KeyError:
            raise KeyError(f"There isn't gene family with the name {name} in the module")

    def __delitem__(self, name):
        try:
            del self._families_getter[name]
        except KeyError:
            raise KeyError(f"There isn't gene family with the name {name} in the module")

    @property
    def families(self) -> Generator[GeneFamily, None, None]:
        for family in self._families_getter.values():
            yield family


class GeneContext:
    """
    A class used to represent a gene context

    :param gc_id : identifier of the Gene context
    :param families: Gene families related to the GeneContext
    """

    def __init__(self, gc_id: int, families: set = None):
        self.ID = gc_id
        self.families = set()
        if families is not None:
            if not all(isinstance(fam, GeneFamily) for fam in families):
                raise Exception("You provided elements that were not GeneFamily object."
                                " GeneContext are only made of GeneFamily")
            self.families |= set(families)

    def add_family(self, family: GeneFamily):
        """
        Allow to add one family in the GeneContext
        :param family: family to add
        """
        if not isinstance(family, GeneFamily):
            raise Exception("You did not provide a GenFamily object. Modules are only made of GeneFamily")
        self.families.add(family)
