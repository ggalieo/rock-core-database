FROM pgvector/pgvector:pg16

# PostGIS on top of the pgvector PostgreSQL 16 image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       postgresql-16-postgis-3 \
       postgresql-16-postgis-3-scripts \
    && rm -rf /var/lib/apt/lists/*

# schema.sql + seed.sql are mounted by docker-compose into
# /docker-entrypoint-initdb.d and run on first initialization.
