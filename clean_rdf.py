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
        
        # Fix date datatypes - ensure all dates have XSD date datatype
        dcterms = Namespace("http://purl.org/dc/terms/")
        dc = Namespace("http://purl.org/dc/elements/1.1/")
        xsd = Namespace("http://www.w3.org/2001/XMLSchema#")
        
        # Find and fix date literals without proper datatype
        date_properties = [dcterms.created, dcterms.modified, dc.date]
        for date_prop in date_properties:
            for s, p, o in list(g.triples((None, date_prop, None))):
                if isinstance(o, Literal) and o.datatype != xsd.date:
                    # Remove old literal and add with proper datatype
                    g.remove((s, p, o))
                    g.add((s, p, Literal(str(o), datatype=xsd.date)))
        
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
        g.add((knil[''], dcterms.modified, Literal("2025-09-02", datatype=xsd.date)))
        g.add((knil[''], dcterms.isVersionOf, og_nil))
        g.add((knil[''], owl.versionInfo, Literal("1.0")))
        g.add((knil[''], RDFS.comment, Literal("Derivative work of OGC nil reasons with uppercase-only concepts and hasTopConcept relationships. Intended for contribution back to OGC.", lang="en")))
        
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