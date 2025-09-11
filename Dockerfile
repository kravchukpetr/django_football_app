# Use the official PostgreSQL image
FROM postgres:15

# Set environment variables for PostgreSQL
ENV POSTGRES_DB=football_stats
ENV POSTGRES_USER=football_user
ENV POSTGRES_PASSWORD=football_password

# Create a directory for initialization scripts
RUN mkdir -p /docker-entrypoint-initdb.d

# Copy initialization script (optional)
# COPY init.sql /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# The postgres image automatically starts the PostgreSQL server
