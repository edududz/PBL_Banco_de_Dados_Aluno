"""Aplicação de manutenção industrial — cliente de linha de comando.

Uso interativo: python app.py
Uso direto:    python app.py --help
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from database import verificar_conexao
from importacao import importar_csv
from operacoes import (atualizar_preco, atualizar_status, consultar_ordem,
                       encerrar_ordem, listar_componentes, listar_estoques,
                       retirar_pecas)
from relatorios import consultar_custo_os, consultar_historico
from uso_repetido import consultar_indicador_repetidamente, sessoes_retidas


def imprimir_tabela(cabecalhos: list[str], linhas: list[tuple]) -> None:
    if not linhas:
        print('(nenhum registro encontrado)')
        return
    colunas = [[str(v) if v is not None else 'NULL' for v in linha]
               for linha in linhas]
    larguras = [min(42, max(len(str(cab)), *(len(linha[i]) for linha in colunas)))
                for i, cab in enumerate(cabecalhos)]
    def formatar(linha):
        return ' | '.join(str(v)[:largura].ljust(largura)
                          for v, largura in zip(linha, larguras))
    print(formatar(cabecalhos))
    print('-+-'.join('-' * largura for largura in larguras))
    for linha in colunas:
        print(formatar(linha))
    print(f'\n{len(linhas)} registro(s).')


def _data(valor: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise ValueError('Data inválida; utilize AAAA-MM-DD.') from exc


def _decimal(valor: str) -> Decimal:
    try:
        return Decimal(valor.replace(',', '.'))
    except Exception as exc:
        raise ValueError('Informe um número decimal válido.') from exc


def executar(acao: str, **args) -> None:
    if acao == 'verificar':
        info = verificar_conexao()
        print('Conexão estabelecida:')
        for nome, valor in info.items():
            print(f'  {nome}: {valor}')
    elif acao == 'estoques':
        imprimir_tabela(['Depósito', 'Componente', 'Descrição', 'Saldo', 'Atualizado em'],
                       listar_estoques())
    elif acao == 'componentes':
        imprimir_tabela(['Código', 'Descrição', 'Preço', 'Fornecedor cadastro',
                        'Fornecedor ficha', 'Telefone cadastro', 'Telefone ficha'],
                       listar_componentes())
    elif acao == 'historico':
        linhas = consultar_historico(args['componente'],
                                   _data(args['inicio']), _data(args['fim']),
                                   args.get('limite', 100))
        imprimir_tabela(['ID', 'Data/hora', 'Depósito', 'Tipo', 'Quantidade', 'Observação'],
                       linhas)
    elif acao == 'custo':
        resultado = consultar_custo_os(args['os'])
        if resultado is None:
            print('Não há resultado para essa ordem.')
        else:
            print(f'Ordem {resultado[0]}: custo calculado R$ {resultado[1]:.2f}')
    elif acao == 'retirar':
        resultado = retirar_pecas(args['deposito'], args['componente'],
                                int(args['quantidade']), args.get('os'),
                                args.get('tempo_processamento', 0.15))
        print('Operação registrada:', resultado)
    elif acao == 'encerrar':
        resultado = encerrar_ordem(args['os'], args['descricao'],
                                  _decimal(str(args['valor'])),
                                  bool(args.get('simular_falha', False)))
        print('Encerramento registrado:', resultado)
    elif acao == 'importar':
        print('Importação:', importar_csv(args['arquivo'], args['lote']))
    elif acao == 'preco':
        atualizar_preco(args['componente'], _decimal(str(args['valor'])))
        print('Preço de catálogo atualizado.')
    elif acao == 'status':
        atualizar_status(args['os'], args['status'])
        print('Status atualizado:', consultar_ordem(args['os']))
    elif acao == 'repeticoes':
        try:
            resultado = consultar_indicador_repetidamente(int(args['vezes']))
            imprimir_tabela(['Iteração', 'Quantidade de OS', 'Sessões retidas'], resultado)
        finally:
            print(f'Sessões da aplicação mantidas até seu encerramento: {sessoes_retidas()}')
    else:
        raise ValueError(f'Comando desconhecido: {acao}')


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Sistema de manutenção industrial (PostgreSQL).')
    sub = parser.add_subparsers(dest='comando')
    for nome in ('verificar', 'estoques', 'componentes'):
        sub.add_parser(nome)

    p = sub.add_parser('historico', help='Consulta de movimentações por componente e período.')
    p.add_argument('--componente', required=True)
    p.add_argument('--inicio', required=True, help='AAAA-MM-DD')
    p.add_argument('--fim', required=True, help='AAAA-MM-DD')
    p.add_argument('--limite', type=int, default=100)

    p = sub.add_parser('custo', help='Relatório de custo da ordem de serviço.')
    p.add_argument('--os', required=True)

    p = sub.add_parser('retirar', help='Retirada de peças do depósito.')
    p.add_argument('--deposito', required=True)
    p.add_argument('--componente', required=True)
    p.add_argument('--quantidade', required=True, type=int)
    p.add_argument('--os')
    p.add_argument('--tempo-processamento', type=float, default=0.15)

    p = sub.add_parser('encerrar', help='Encerramento de ordem de serviço.')
    p.add_argument('--os', required=True)
    p.add_argument('--descricao', default='Ajuste e encerramento')
    p.add_argument('--valor', default='0.00')
    p.add_argument('--simular-falha', action='store_true')

    p = sub.add_parser('importar', help='Importação de movimentações de CSV.')
    p.add_argument('--arquivo', required=True)
    p.add_argument('--lote', required=True)

    p = sub.add_parser('preco', help='Alteração do preço de catálogo.')
    p.add_argument('--componente', required=True)
    p.add_argument('--valor', required=True)

    p = sub.add_parser('status', help='Atualização de status de OS.')
    p.add_argument('--os', required=True)
    p.add_argument('--status', required=True,
                   choices=('ABERTA', 'EM_EXECUCAO', 'ENCERRADA'))

    p = sub.add_parser('repeticoes', help='Consultas repetidas do indicador.')
    p.add_argument('--vezes', required=True, type=int)
    return parser


def menu_interativo() -> None:
    opcoes = {
        '1': ('Verificar conexão', lambda: executar('verificar')),
        '2': ('Consultar estoques', lambda: executar('estoques')),
        '3': ('Consultar ficha de componentes', lambda: executar('componentes')),
        '4': ('Histórico de movimentações', lambda: executar('historico',
              componente=input('Código do componente: '),
              inicio=input('Data inicial (AAAA-MM-DD): '),
              fim=input('Data final (AAAA-MM-DD): '))),
        '5': ('Relatório de custos de OS', lambda: executar('custo',
              os=input('Número da OS: '))),
        '6': ('Retirar peças', lambda: executar('retirar',
              deposito=input('Depósito: '),
              componente=input('Componente: '),
              quantidade=int(input('Quantidade: ')),
              os=input('OS (pode deixar vazio): ').strip() or None)),
        '7': ('Encerrar ordem de serviço', lambda: executar('encerrar',
              os=input('Número da OS: '),
              descricao=input('Descrição do serviço final: '),
              valor=input('Valor do serviço (ex.: 50.00): '),
              simular_falha=input('Simular indisponibilidade externa? (s/N): ')
                              .strip().lower() == 's')),
        '8': ('Importar arquivo CSV', lambda: executar('importar',
              arquivo=input('Caminho do arquivo CSV: '),
              lote=input('Código do lote externo: '))),
        '9': ('Atualizar preço de catálogo', lambda: executar('preco',
              componente=input('Componente: '),
              valor=input('Novo preço: '))),
        '10': ('Atualizar status da OS', lambda: executar('status',
               os=input('Número da OS: '),
               status=input('Status (ABERTA/EM_EXECUCAO/ENCERRADA): '))),
        '11': ('Consultar indicador repetidamente', lambda: executar('repeticoes',
               vezes=int(input('Número de consultas (1 a 20): ')))),
    }
    while True:
        print('\n=== SISTEMA INDUSTRIAL | Menu principal ===')
        for codigo, (nome, _) in opcoes.items():
            print(f'{codigo:>2}. {nome}')
        print(' 0. Sair')
        escolha = input('Escolha: ').strip()
        if escolha == '0':
            break
        try:
            if escolha not in opcoes:
                print('Opção inválida.')
            else:
                opcoes[escolha][1]()
        except (Exception, KeyboardInterrupt) as exc:
            print(f'Operação não concluída: {exc}', file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = criar_parser()
    args = parser.parse_args(argv)
    if args.comando is None:
        menu_interativo()
        return 0
    try:
        executar(args.comando, **vars(args))
    except Exception as exc:
        print(f'Operação não concluída: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
