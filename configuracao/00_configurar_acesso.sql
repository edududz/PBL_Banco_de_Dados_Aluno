-- Configuracao inicial de acesso do sistema legado.
-- Executar com psql, conectado ao banco restaurado, usando a conta administradora.
\set ON_ERROR_STOP on
\if :{?restauracao_interativa}
SELECT NOT EXISTS (
  SELECT 1 FROM pg_authid WHERE rolname = 'pbl_app' AND rolpassword IS NOT NULL
) AS pbl_senha_pendente \gset
\endif
DO $role$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pbl_app') THEN
    CREATE ROLE pbl_app LOGIN;
  END IF;
END
$role$;
SELECT format('GRANT CONNECT ON DATABASE %I TO pbl_app;', current_database()) \gexec
GRANT USAGE, CREATE ON SCHEMA industria TO pbl_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA industria TO pbl_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA industria TO pbl_app;

\if :{?restauracao_interativa}
  \if :pbl_senha_pendente
    \password pbl_app
    DO $senha$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_authid WHERE rolname = 'pbl_app' AND rolpassword IS NOT NULL
      ) THEN
        RAISE EXCEPTION 'Informe uma senha para pbl_app ao restaurar o banco.';
      END IF;
    END
    $senha$;
  \endif
\endif
