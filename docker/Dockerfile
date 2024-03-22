FROM postgres:13.3

ENV POSTGRES_DB="database"
ENV POSTGRES_USER="user"
ENV POSTGRES_PASSWORD="password"

EXPOSE 5432

COPY docker-entrypoint-initdb.d /docker-entrypoint-initdb.d
