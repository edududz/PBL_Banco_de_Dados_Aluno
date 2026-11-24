"""Importação de movimentações recebidas de sistemas externos."""
from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from database import conectar

COLUNAS = {'registro_origem', 'deposito', 'componente', 'tipo',
           'quantidade', 'valor_unitario'}


def importar_csv(arquivo: str | Path, chave_lote: str) -> dict:
    caminho = Path(arquivo).expanduser().resolve()
    if not caminho.is_file():
        raise FileNotFoundError(f'Arquivo CSV não encontrado: {caminho}')
    if not chave_lote.strip():
        raise ValueError('Informe a identificação do lote.')

    with caminho.open('r', newline='', encoding='utf-8-sig') as arquivo_csv:
        leitor = csv.DictReader(arquivo_csv, delimiter=';')
        if leitor.fieldnames is None or not COLUNAS.issubset(leitor.fieldnames):
            raise ValueError('O CSV deve conter: ' + ', '.join(sorted(COLUNAS)))
        linhas = list(leitor)
    if not linhas:
        raise ValueError('Não há linhas no arquivo de importação.')

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO industria.importacoes
                    (chave_lote, nome_arquivo, status)
                VALUES (%s, %s, 'INICIADA') RETURNING id
            """, (chave_lote, caminho.name))
            importacao_id = cur.fetchone()[0]
            processadas = 0
            for linha in linhas:
                cur.execute("""
                    SELECT d.id, c.id
                    FROM industria.depositos d
                    CROSS JOIN industria.componentes c
                    WHERE d.codigo = %s AND c.codigo = %s
                """, (linha['deposito'], linha['componente']))
                ids = cur.fetchone()
                if ids is None:
                    raise ValueError('Depósito/componente inexistente: ' + str(linha))

                deposito_id, componente_id = ids
                tipo = linha['tipo'].strip().upper()
                if tipo not in ('ENTRADA', 'SAIDA'):
                    raise ValueError('Tipo inválido: ' + tipo)
                quantidade = int(linha['quantidade'])
                preco = Decimal(linha['valor_unitario'])
                if quantidade <= 0 or preco < 0:
                    raise ValueError('Quantidade/preço inválidos no CSV.')
                delta = quantidade if tipo == 'ENTRADA' else -quantidade

                cur.execute("""
                    INSERT INTO industria.movimentacoes
                        (deposito_id, componente_id, importacao_id,
                         registro_origem, tipo, quantidade,
                         valor_unitario_aplicado, observacao)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Importação externa')
                """, (deposito_id, componente_id, importacao_id,
                      linha['registro_origem'], tipo, quantidade, preco))

                cur.execute("""
                    UPDATE industria.estoques
                    SET quantidade = quantidade + %s, atualizado_em = now()
                    WHERE deposito_id = %s AND componente_id = %s
                """, (delta, deposito_id, componente_id))
                if cur.rowcount != 1:
                    raise ValueError('Saldo de estoque não cadastrado para o item: ' + str(linha))
                processadas += 1

            cur.execute("""
                UPDATE industria.importacoes
                SET status = 'CONCLUIDA', finalizada_em = now()
                WHERE id = %s
            """, (importacao_id,))
    return {'lote': chave_lote, 'importacao_id': importacao_id,
            'linhas_processadas': processadas}
