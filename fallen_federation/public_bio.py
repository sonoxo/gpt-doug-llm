"""Authoritative public biological-data source registry.

The registry is metadata-only. It does not download protected human data, scrape
restricted systems, or infer consent. Adapters should preserve source provenance,
terms of use, release date, and dataset identifiers.
"""

PUBLIC_BIO_SOURCES = {
    "clinicaltrials": {
        "name": "ClinicalTrials.gov",
        "kind": "clinical_trial_registry",
        "access": "public",
        "base": "https://clinicaltrials.gov/",
    },
    "gdc": {
        "name": "NCI Genomic Data Commons",
        "kind": "cancer_genomics",
        "access": "public_and_controlled",
        "base": "https://portal.gdc.cancer.gov/",
    },
    "geo": {
        "name": "NCBI Gene Expression Omnibus",
        "kind": "functional_genomics",
        "access": "public",
        "base": "https://www.ncbi.nlm.nih.gov/geo/",
    },
    "sra": {
        "name": "NCBI Sequence Read Archive",
        "kind": "sequence_archive",
        "access": "public_and_controlled",
        "base": "https://www.ncbi.nlm.nih.gov/sra",
    },
    "pubmed": {
        "name": "PubMed",
        "kind": "biomedical_literature",
        "access": "public_metadata",
        "base": "https://pubmed.ncbi.nlm.nih.gov/",
    },
    "uniprot": {
        "name": "UniProt",
        "kind": "protein_knowledge",
        "access": "public",
        "base": "https://www.uniprot.org/",
    },
}


def source_catalog() -> list[dict]:
    return [{"id": key, **value} for key, value in sorted(PUBLIC_BIO_SOURCES.items())]


def public_only() -> list[dict]:
    return [
        item
        for item in source_catalog()
        if item["access"] in {"public", "public_metadata"}
    ]
