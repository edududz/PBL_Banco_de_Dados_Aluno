"""Conexão com o PostgreSQL usado pelo sistema de manutenção industrial.

As configurações são lidas do .env local (não versionado) ou do ambiente.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg

load_dotenv(Path(__file__).with_name('.env'))


def conectar() -> psycopg.Connection:
    """Cria uma conexão independente para uma operação da aplicação."""
    configuracao = {
        'host': os.getenv('PGHOST', '127.0.0.1'),
        'port': int(os.getenv('PGPORT', '5432')),
        'dbname': os.getenv('PGDATABASE', 'pbl_industria_homologacao'),
        'user': os.getenv('PGUSER', 'pbl_app'),
        'connect_timeout': 5,
        'application_name': 'pbl-manutencao',
    }
    senha = os.getenv('PGPASSWORD')
    if senha:
        configuracao['password'] = senha
    return psycopg.connect(**configuracao)


def verificar_conexao() -> dict:
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT current_database(), current_user, current_setting('server_version'),
                       (SELECT COUNT(*) FROM industria.componentes)
            """)
            banco, usuario, versao, componentes = cur.fetchone()
            return {'banco': banco, 'usuario': usuario,
                    'versao': versao, 'componentes': componentes}
