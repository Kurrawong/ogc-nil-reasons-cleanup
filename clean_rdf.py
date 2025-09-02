#!/usr/bin/env python3

import os
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import SKOS, RDF, RDFS

def clean_rdf():
    download_dir = Path("download")
    cleaned_dir = Path("cleaned")
    cleaned_dir.mkdir(exist_ok=True)

    additional_namespaces = {
        'ogc': Namespace("http://www.opengis.net/def/"),
        'gml': Namespace("http://www.opengis.net/doc/gml#"),
        'nil': Namespace("http://www.opengis.net/def/nil/OGC/0/"),
        'status': Namespace("http://www.opengis.net/def/status/"),
        'knil': Namespace("https://kurrawong.ai/vocab/nil/1.0/"),
        'mm': Namespace("http://www.opengis.net/def/metamodel/"),
        'mmon': Namespace("http://www.opengis.net/def/metamodel/ogc-na/"),
    }
    
    for rdf_file in download_dir.glob("*.ttl"):
        print(f"Processing {rdf_file}")
        
        g = Graph()
        g.parse(rdf_file, format="turtle")
        
        # Bind namespaces
        for prefix, ns in additional_namespaces.items():
            g.bind(prefix, ns)
        
        # Remove uppercase versions, keep only lowercase
        lowercase_concepts = []
        for s, p, o in g:
            if isinstance(s, URIRef) and '/ogc/' in str(s):
                lowercase_concepts.append(s)
        
        for concept in lowercase_concepts:
            g.remove((concept, None, None))
            g.remove((None, None, concept))
        
        # Remove implementation artifacts
        mm = additional_namespaces['mm']
        g.remove((None, mm.hasProfile, None))
        g.remove((None, RDFS.seeAlso, None))
        
        # # Change Collection to ConceptScheme
        # for s, p, o in g.triples((None, RDF.type, SKOS.Collection)):
        #     g.remove((s, RDF.type, SKOS.Collection))
        #     g.add((s, RDF.type, SKOS.ConceptScheme))
        
        # Add versioning metadata for your derivative work
        knil = additional_namespaces['knil']
        og_nil = additional_namespaces['ogc']['nil']
        dcterms = Namespace("http://purl.org/dc/terms/")
        owl = Namespace("http://www.w3.org/2002/07/owl#")
        xsd = Namespace("http://www.w3.org/2001/XMLSchema#")
        
        # Create your versioned ConceptScheme
        g.add((knil[''], RDF.type, SKOS.ConceptScheme))
        g.add((knil[''], dcterms.title, Literal("Nil reasons (Kurrawong derivative v1.0)", lang="en")))
        g.add((knil[''], dcterms.creator, URIRef("https://orcid.org/0000-0002-3322-1868")))
        g.add((knil[''], dcterms.modified, Literal("2025-01-01", datatype=xsd.date)))
        g.add((knil[''], dcterms.isVersionOf, og_nil))
        g.add((knil[''], owl.versionInfo, Literal("1.0")))
        g.add((knil[''], RDFS.comment, Literal("Derivative work of OGC nil reasons with lowercase-only concepts and proper hasTopConcept relationships. Intended for contribution back to OGC.", lang="en")))
        
        # Update concepts to point to your scheme
        for concept in g.subjects(SKOS.inScheme, og_nil):
            if str(concept).startswith('http://www.opengis.net/def/nil/ogc/0/'):
                g.add((concept, SKOS.inScheme, knil['']))
        
        # Add hasTopConcept triples (inverse of inScheme)
        for s, p, o in g.triples((None, SKOS.inScheme, None)):
            if s != URIRef("http://www.opengis.net/def/nil/"):
                g.add((o, SKOS.hasTopConcept, s))
        
        # Output cleaned turtle
        output_file = cleaned_dir / "updated.ttl"
        g.serialize(destination=output_file, format="turtle")
        print(f"Cleaned file saved to {output_file}")

if __name__ == "__main__":
    clean_rdf()