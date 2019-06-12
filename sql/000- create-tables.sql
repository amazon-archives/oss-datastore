CREATE TYPE source_type AS ENUM (
  'github_v3',
  'github_v4'
);
CREATE TABLE dead_letter_queue (
  id SERIAL PRIMARY KEY NOT NULL,
  source source_type NOT NULL,
  request_time TIMESTAMP NOT NULL,
  response JSONB NOT NULL
);
