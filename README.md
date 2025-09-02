# Nil Types Vocabulary - Kurrawong Derivative

A cleaned derivative of the OGC nil reasons vocabulary with SKOS Concept Scheme semantics and lowercase-only concept URIs.

## Changes Made

### Data Cleaning (`clean_rdf.py`)

1. **Date Standardization**: All date literals now use XSD date datatype (`^^xsd:date`)

2. **Label Standardization**: 
   - Removed duplicate `rdfs:label` statements
   - Converted to SKOS semantics:
     - `skos:prefLabel` for lowercase versions (e.g., `"unknown"@en`)
     - `skos:altLabel` for capitalized versions (e.g., `"Unknown"@en`)
   - Only retained labels with language tags (removed untagged duplicates)

3. **Concept URI Cleanup**: Removed lowercase concept versions, keeping only uppercase URIs. NB the lowercase versions have definitions that are not the labels.

4. **Metadata Removal**: Stripped implementation/technical artifacts (`hasProfile`, `seeAlso` references)

5. **Versioning**: Added derivative work metadata with Kurrawong namespace

## Files

- `download/original.ttl` - Original OGC nil reasons vocabulary
- `clean_rdf.py` - Python script performing all transformations
- `cleaned/updated.ttl` - Output with cleaned, standardized vocabulary

## Usage

```bash
python clean_rdf.py
```