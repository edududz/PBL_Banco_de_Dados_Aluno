"""Operação de consulta de disponibilidade executada repetidamente."""
from __future__ import annotations

from database import conectar

# Limite interno definido pela configuração da aplicação legado.
MAX_SESSOES_ABERTAS = 8
_SESSOES = []


def consultar_indicador_repetidamente(vezes: int) -> list[tuple]:
    if not 1 <= vezes <= 20:
        raise ValueError('Utilize de 1 a 20 repetições por teste.')

    resultados = []
    for indice in range(vezes):
        if len(_SESSOES) >= MAX_SESSOES_ABERTAS:
            raise RuntimeError('A aplicação atingiu o limite de sessões simultâneas.')
        conn = conectar()
        _SESSOES.append(conn)
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM industria.ordens_servico')
            total_os = cur.fetchone()[0]
        resultados.append((indice + 1, total_os, len(_SESSOES)))
    return resultados


def sessoes_retidas() -> int:
    return len(_SESSOES)
