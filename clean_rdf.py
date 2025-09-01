#!/usr/bin/env python3

import os
from pathlib import Path
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import SKOS, RDF, RDFS

def clean_rdf():
    download_dir = Path("download")
    cleaned_dir = Path("cleaned")
    cleaned_dir.mkdir(exist_ok=True)

    additional_namespaces = {
        'ogc': Namespace("http://www.opengis.net/def/"),
        'gml': Namespace("http://www.opengis.net/doc/gml#"),
        'nil': Namespace("http://www.opengis.net/def/nil/ogc/0/"),
        'status': Namespace("http://www.opengis.net/def/status/"),
    }
    
    for rdf_file in download_dir.glob("*.ttl"):
        print(f"Processing {rdf_file}")
        
        g = Graph()
        g.parse(rdf_file, format="turtle")
        
        # Bind namespaces
        for prefix, ns in additional_namespaces.items():
            g.bind(prefix, ns)
        
        # Add hasTopConcept triples (inverse of inScheme)
        for s, p, o in g.triples((None, SKOS.inScheme, None)):
            g.add((o, SKOS.hasTopConcept, s))
        
        # Output cleaned turtle
        output_file = cleaned_dir / rdf_file.name
        g.serialize(destination=output_file, format="turtle")
        print(f"Cleaned file saved to {output_file}")

if __name__ == "__main__":
    clean_rdf()