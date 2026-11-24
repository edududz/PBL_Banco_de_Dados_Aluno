"""Relatórios operacionais, como apresentados na aplicação original."""
from __future__ import annotations

from datetime import date, timedelta

from database import conectar


def consultar_historico(componente_codigo: str, inicio: date, fim: date,
                       limite: int = 100) -> list[tuple]:
    if inicio > fim:
        raise ValueError('A data inicial deve anteceder ou coincidir com a final.')
    if not 1 <= limite <= 500:
        raise ValueError('O limite deve estar entre 1 e 500.')
    # Fim de intervalo exclusivo para incluir integralmente o último dia.
    fim_exclusivo = fim + timedelta(days=1)
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT m.id, m.momento, d.codigo, m.tipo,
                       m.quantidade, m.observacao
                FROM industria.movimentacoes m
                JOIN industria.componentes c ON c.id = m.componente_id
                JOIN industria.depositos d ON d.id = m.deposito_id
                WHERE c.codigo = %s
                  AND m.momento >= %s AND m.momento < %s
                ORDER BY m.momento DESC, m.id DESC
                LIMIT %s
            """, (componente_codigo, inicio, fim_exclusivo, limite))
            return cur.fetchall()


def consultar_custo_os(numero_os: str) -> tuple | None:
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.numero,
                       SUM(i.quantidade * c.preco_atual) + SUM(s.valor) AS total
                FROM industria.ordens_servico o
                JOIN industria.itens_ordem i ON i.ordem_servico_id = o.id
                JOIN industria.componentes c ON c.id = i.componente_id
                JOIN industria.servicos_ordem s ON s.ordem_servico_id = o.id
                WHERE o.numero = %s
                GROUP BY o.numero
            """, (numero_os,))
            return cur.fetchone()
