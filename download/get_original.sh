curl -X POST https://defs.opengis.net/prez-backend/sparql \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "query=PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
DESCRIBE ?x {
  { BIND(<http://www.opengis.net/def/nil> as ?x) }
  UNION
  { ?x a skos:Concept ; skos:inScheme <http://www.opengis.net/def/nil> }
}" \
  > original.ttl