"""Operações de almoxarifado e de ordens de serviço."""
from __future__ import annotations

import time
from decimal import Decimal
from collections.abc import Callable

from database import conectar


def listar_estoques() -> list[tuple]:
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.codigo, c.codigo, c.descricao, e.quantidade,
                       e.atualizado_em
                FROM industria.estoques e
                JOIN industria.depositos d ON d.id = e.deposito_id
                JOIN industria.componentes c ON c.id = e.componente_id
                ORDER BY d.codigo, c.codigo
            """)
            return cur.fetchall()


def listar_componentes() -> list[tuple]:
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.codigo, c.descricao, c.preco_atual,
                       f.nome AS fornecedor_cadastrado,
                       c.fornecedor_nome_cache AS fornecedor_na_ficha,
                       f.telefone AS telefone_cadastrado,
                       c.fornecedor_telefone_cache AS telefone_na_ficha
                FROM industria.componentes c
                JOIN industria.fornecedores f ON f.id = c.fornecedor_id
                ORDER BY c.codigo
            """)
            return cur.fetchall()


def retirar_pecas(deposito_codigo: str, componente_codigo: str,
                  quantidade: int, numero_os: str | None = None,
                  tempo_processamento: float = 0.15,
                  _sincronizacao_teste: Callable[[], None] | None = None) -> dict:
    """Registra uma solicitação de retirada de material.

    O intervalo representa o tempo de confirmação de uma solicitação pelo
    serviço legado de almoxarifado; o chamador pode ajustá-lo no laboratório.
    """
    if quantidade <= 0:
        raise ValueError('A quantidade deve ser maior que zero.')
    if tempo_processamento < 0 or tempo_processamento > 5:
        raise ValueError('O tempo de processamento deve estar entre 0 e 5 segundos.')

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.deposito_id, e.componente_id, e.quantidade,
                       c.preco_atual
                FROM industria.estoques e
                JOIN industria.depositos d ON d.id = e.deposito_id
                JOIN industria.componentes c ON c.id = e.componente_id
                WHERE d.codigo = %s AND c.codigo = %s
            """, (deposito_codigo, componente_codigo))
            registro = cur.fetchone()
            if registro is None:
                raise ValueError('Combinação de depósito e componente não encontrada.')

            deposito_id, componente_id, saldo, preco = registro
            if saldo < quantidade:
                raise ValueError(f'Estoque insuficiente: há {saldo}, solicitadas {quantidade}.')

            os_id = None
            if numero_os:
                cur.execute('SELECT id FROM industria.ordens_servico WHERE numero = %s',
                            (numero_os,))
                ordem = cur.fetchone()
                if ordem is None:
                    raise ValueError('Ordem de serviço não encontrada.')
                os_id = ordem[0]

            # Verificação administrativa externa, simulada pelo intervalo de processamento.
            if _sincronizacao_teste is not None:
                _sincronizacao_teste()
            else:
                time.sleep(tempo_processamento)

            cur.execute("""
                UPDATE industria.estoques
                SET quantidade = quantidade - %s, atualizado_em = now()
                WHERE deposito_id = %s AND componente_id = %s
                RETURNING quantidade
            """, (quantidade, deposito_id, componente_id))
            saldo_final = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO industria.movimentacoes
                    (deposito_id, componente_id, ordem_servico_id, tipo,
                     quantidade, valor_unitario_aplicado, observacao)
                VALUES (%s, %s, %s, 'SAIDA', %s, %s, 'Retirada pela aplicação')
                RETURNING id
            """, (deposito_id, componente_id, os_id, quantidade, preco))
            movimento_id = cur.fetchone()[0]

            if os_id is not None:
                cur.execute("""
                    INSERT INTO industria.itens_ordem
                        (ordem_servico_id, componente_id, quantidade,
                         valor_unitario_aplicado)
                    VALUES (%s, %s, %s, %s)
                """, (os_id, componente_id, quantidade, preco))

    return {'saldo_anterior': saldo, 'saldo_final': saldo_final,
            'movimentacao_id': movimento_id, 'quantidade': quantidade}


def encerrar_ordem(numero_os: str, descricao_servico: str,
                   valor_servico: Decimal, simular_falha: bool = False) -> dict:
    """Conclui a OS e registra um último serviço executado."""
    if valor_servico < 0:
        raise ValueError('O valor do serviço não pode ser negativo.')

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE industria.ordens_servico
                SET status = 'ENCERRADA', encerrada_em = now()
                WHERE numero = %s AND status <> 'ENCERRADA'
                RETURNING id
            """, (numero_os,))
            linha = cur.fetchone()
            if linha is None:
                raise ValueError('Ordem inexistente ou já encerrada.')
            ordem_id = linha[0]

    # Uma segunda etapa é executada após a atualização da OS.
    if simular_falha:
        raise RuntimeError('O sistema de serviços ficou temporariamente indisponível.')

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO industria.servicos_ordem
                    (ordem_servico_id, descricao, valor)
                VALUES (%s, %s, %s) RETURNING id
            """, (ordem_id, descricao_servico, valor_servico))
            servico_id = cur.fetchone()[0]

    return {'ordem_id': ordem_id, 'servico_id': servico_id,
            'status': 'ENCERRADA'}


def atualizar_preco(componente_codigo: str, novo_preco: Decimal) -> None:
    if novo_preco < 0:
        raise ValueError('O preço não pode ser negativo.')
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE industria.componentes SET preco_atual = %s
                WHERE codigo = %s
            """, (novo_preco, componente_codigo))
            if cur.rowcount != 1:
                raise ValueError('Componente não encontrado.')


def atualizar_status(numero_os: str, novo_status: str) -> None:
    if novo_status not in ('ABERTA', 'EM_EXECUCAO', 'ENCERRADA'):
        raise ValueError('Status inválido.')
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE industria.ordens_servico
                SET status = %s,
                    encerrada_em = CASE WHEN %s = 'ENCERRADA' THEN now() ELSE NULL END
                WHERE numero = %s
            """, (novo_status, novo_status, numero_os))
            if cur.rowcount != 1:
                raise ValueError('Ordem não encontrada.')


def consultar_ordem(numero_os: str) -> tuple | None:
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT numero, status, aberta_em, encerrada_em
                FROM industria.ordens_servico WHERE numero = %s
            """, (numero_os,))
            return cur.fetchone()
