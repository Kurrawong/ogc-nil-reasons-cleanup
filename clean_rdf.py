#!/usr/bin/env python3

import os
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, OWL
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
        'mm': Namespace("http://www.opengis.net/def/metamodel/"),
        'mmon': Namespace("http://www.opengis.net/def/metamodel/ogc-na/"),
        'schema': Namespace("https://schema.org/"),
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
        
        # Update predicates to use schema.org vocabulary
        dcterms = Namespace("http://purl.org/dc/terms/")
        dc = Namespace("http://purl.org/dc/elements/1.1/")
        schema = additional_namespaces['schema']
        xsd = Namespace("http://www.w3.org/2001/XMLSchema#")
        owl = Namespace("http://www.w3.org/2002/07/owl#")
        
        # Convert predicates to schema.org equivalents
        predicate_mappings = {
            dc.creator: schema.creator,
            dcterms.created: schema.dateCreated,
            dcterms.modified: schema.dateModified,
            dcterms.rights: schema.license,
            dc.source: schema.citation,
            dcterms.source: schema.citation,
            dc.rights: schema.copyrightNotice
        }
        
        # Apply predicate mappings
        for old_pred, new_pred in predicate_mappings.items():
            for s, p, o in list(g.triples((None, old_pred, None))):
                g.remove((s, p, o))
                # Ensure dates have proper datatype
                if new_pred in [schema.dateCreated, schema.dateModified] and isinstance(o, Literal):
                    if o.datatype != xsd.date:
                        o = Literal(str(o), datatype=xsd.date)
                g.add((s, new_pred, o))
        
        # Remove dc:date predicates entirely
        g.remove((None, dc.date, None))
        
        # Remove owl:imports predicates
        g.remove((None, owl.imports, None))

        # Remove dc:title "Nil reasons" ;
        g.remove((None, dc.title, None))
        
        # Fix creator and publisher for main concept scheme to meet validation requirements
        og_nil = additional_namespaces['ogc']['nil']
        rob_atkinson_iri = URIRef("https://orcid.org/0000-0002-7878-2693")
        ogc_na_iri = URIRef("http://www.opengis.net/def/entities/bodies/ogcna")

        g.add((rob_atkinson_iri, RDF.type, schema.Person))
        g.add((rob_atkinson_iri, schema.name, Literal("Robert Atkinson")))

        g.add((ogc_na_iri, RDF.type, schema.Organization))

        # remove any collectionView triples
        g.remove((None, additional_namespaces["mmon"]["collectionView"], None))

        # remove owl ontology
        g.remove((None, RDF.type, OWL.Ontology))
        
        # Convert string creator to IRI and add publisher
        for s, p, o in list(g.triples((og_nil, schema.creator, None))):
            if isinstance(o, Literal):  # If creator is a string literal
                g.remove((s, p, o))
                g.add((s, schema.creator, rob_atkinson_iri))
        
        # Add publisher if not present
        if not list(g.triples((og_nil, schema.publisher, None))):
            g.add((og_nil, schema.publisher, ogc_na_iri))
        
        # Organize labels using proper SKOS semantics
        for subject in g.subjects(RDF.type, SKOS.Concept):
            # Get all current labels for this concept
            rdfs_labels = list(g.objects(subject, RDFS.label))
            pref_labels = list(g.objects(subject, SKOS.prefLabel))
            alt_labels = list(g.objects(subject, SKOS.altLabel))
            
            # Group all labels by their lowercase text and language
            all_labels = []
            for label in rdfs_labels + pref_labels + alt_labels:
                if isinstance(label, Literal):
                    all_labels.append((str(label), label.language, label))
            
            # Group by lowercase text and language
            label_groups = {}
            for text, lang, literal in all_labels:
                key = (text.lower(), lang)
                if key not in label_groups:
                    label_groups[key] = []
                label_groups[key].append((text, lang, literal))
            
            # Clear existing labels to rebuild cleanly
            g.remove((subject, RDFS.label, None))
            g.remove((subject, SKOS.prefLabel, None))
            g.remove((subject, SKOS.altLabel, None))
            
            # For each unique label (by lowercase text + language), set proper SKOS labels
            for (text_lower, lang), group in label_groups.items():
                if not lang:  # Skip labels without language tags
                    continue
                    
                # Find lowercase and capitalized versions
                lowercase_versions = [item for item in group if item[0][0].islower()]
                capitalized_versions = [item for item in group if item[0][0].isupper()]
                
                # Set prefLabel (lowercase) and altLabel (capitalized)
                if lowercase_versions:
                    pref_text = lowercase_versions[0][0]  # Use first lowercase version
                    g.add((subject, SKOS.prefLabel, Literal(pref_text, lang=lang)))
                
                if capitalized_versions:
                    alt_text = capitalized_versions[0][0]  # Use first capitalized version
                    g.add((subject, SKOS.altLabel, Literal(alt_text, lang=lang)))
        
        # Add hasTopConcept triples (inverse of inScheme)
        for s, p, o in g.triples((None, SKOS.inScheme, None)):
            if s != URIRef("http://www.opengis.net/def/nil/"):
                g.add((o, SKOS.hasTopConcept, s))
        
        # Output cleaned turtle
        output_file = cleaned_dir / "nils.ttl"
        g.serialize(destination=output_file, format="turtle")
        print(f"Cleaned file saved to {output_file}")

if __name__ == "__main__":
    clean_rdf()