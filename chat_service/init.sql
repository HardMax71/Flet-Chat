-- Check if user exists, create if not
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'chatuser') THEN
      CREATE USER chatuser WITH PASSWORD '${POSTGRES_PASSWORD}';
   END IF;
END
$$;

-- Check if database exists, create if not
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'chatdb') THEN
      CREATE DATABASE chatdb WITH OWNER = chatuser ENCODING = 'UTF8';
   END IF;
END
$$;

-- Grant privileges only if not already granted
GRANT ALL PRIVILEGES ON DATABASE chatdb TO chatuser;
