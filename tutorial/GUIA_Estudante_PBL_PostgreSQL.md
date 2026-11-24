---
title: "PBL de Banco de Dados | Preparação do ambiente"
subtitle: "Guia do estudante - PostgreSQL 18 (Docker ou Windows) e aplicação Python"
date: "2026/2"
lang: pt-BR
---

# Objetivo

Neste trabalho, você receberá uma **cópia de um banco de dados industrial existente** e uma **aplicação Python inicial**. Antes de investigar os relatos do cliente, será necessário restaurar o banco, configurar o acesso e comprovar que a aplicação funciona no seu computador.

Este guia ensina **como preparar o ambiente**. Ele não descreve os defeitos do sistema nem fornece a solução dos incidentes. Escolha **um dos dois caminhos**: **A. PostgreSQL 18 no Docker** ou **B. PostgreSQL 18 instalado diretamente no Windows**. Em seguida, continue na seção **C. Aplicação Python**.

## 1. Arquivos recebidos e requisitos

A organização esperada é:

```text
PBL_Banco_de_Dados_Aluno/
|-- industria_homologacao_500k.dump   <- incluído no ZIP
|-- aplicacao/
|   |-- app.py
|   |-- database.py
|   |-- operacoes.py, relatorios.py, importacao.py, uso_repetido.py
|   |-- requirements.txt
|   `-- .env.example
|-- configuracao/
|   |-- restaurar_pbl.ps1
|   `-- 00_configurar_acesso.sql
|-- docker/
|   |-- compose.yaml
|   `-- .env.example
`-- tutorial/
    `-- GUIA_Estudante_PBL_PostgreSQL.pdf
```

Instale ou tenha disponível: **Windows 10/11**, **PowerShell**, **Python 3.11 ou superior** e **PostgreSQL 18** (direto no Windows ou pelo Docker Desktop). Uma conexão à internet pode ser necessária na primeira instalação do Python e das dependências. O banco utiliza o schema `industria`.

**Antes de começar:** extraia todo o ZIP em uma pasta local. O arquivo `industria_homologacao_500k.dump` já vem no ZIP, na raiz da pasta extraída. Abra o PowerShell **nessa pasta principal**. Os comandos abaixo assumem esse local como ponto de partida.

> **Preserve os dados.** Não execute `docker compose down -v`, não remova volumes e não restaure sobre um banco com informações importantes. O banco do trabalho se chamará `pbl_industria_homologacao`.

# A. Caminho Docker Desktop

## A1. Iniciar o PostgreSQL 18

Se você já possui o Compose utilizado nas aulas, pode mantê-lo, desde que ele disponibilize o PostgreSQL 18 em `127.0.0.1:5432`, use o serviço `db` e tenha o administrador `aluno`. **Não crie outro contêiner na mesma porta.** Caso esteja começando do zero, use o `compose.yaml` fornecido na pasta `docker`. Esse arquivo tem o nome de projeto `pbl-estudante`, para não reutilizar os contêineres do Compose de aula.

**Para iniciar um Compose novo**, na **pasta principal** do PBL:

```powershell
Copy-Item .\docker\.env.example .\docker\.env
notepad .\docker\.env
```

Altere `POSTGRES_PASSWORD` para uma **senha local de sua escolha**. Esse arquivo é utilizado apenas pelo Docker Compose; não é o mesmo `.env` da aplicação. A senha de um volume já inicializado não muda simplesmente ao editar o arquivo. Se a porta 5432 já estiver ocupada por outro PostgreSQL, use `POSTGRES_PORT=55432` e, na etapa C, `PGPORT=55432`.

**Para todos os comandos Docker**, entre na pasta `docker` do kit e defina o arquivo Compose que será utilizado:

```powershell
Set-Location .\docker
$ComposeFile = (Resolve-Path .\compose.yaml).Path
```

Se você **já utiliza outro `compose.yaml` das aulas**, substitua o valor de `$ComposeFile` pelo **caminho completo** desse arquivo, por exemplo:

```powershell
$ComposeFile = "C:\CAMINHO\DO\COMPOSE_DAS_AULAS\compose.yaml"
```

A partir daqui, sempre utilizaremos **`docker compose -f $ComposeFile`**, evitando o erro de configuração não encontrada:

```powershell
docker compose -f $ComposeFile up -d --wait
docker compose -f $ComposeFile exec -T db psql -U aluno -d laboratorio -c "SELECT current_user, current_database();"
```

O resultado deve identificar o usuário `aluno` e o banco `laboratorio`. Se o comando falhar por usuário ou senha, verifique como seu volume PostgreSQL foi inicialmente configurado; **não exclua o volume**.

## A2. Restaurar o dump e preparar o acesso

No PowerShell, dentro da pasta `docker`, execute:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ..\configuracao\restaurar_pbl.ps1 -Modo Docker `
  -ComposeFile $ComposeFile
```

O comando cria o banco, restaura o dump e configura `pbl_app`. Quando solicitado, escolha e confirme a senha local da aplicação. Se a conta já existir na mesma instância, use a senha que ela já possui. Você vai informar essa senha na etapa C2.

Se o comando informar que o banco já existe, confira a instalação antes de prosseguir. Se houve uma falha depois da criação do banco, o banco pode ter ficado vazio. Consulte o professor antes de repetir a restauração.

## A3. Conferir o banco restaurado

Ainda na pasta `docker`:

```powershell
docker compose -f $ComposeFile exec -T db psql -U aluno -d pbl_industria_homologacao `
  -c "SELECT COUNT(*) AS tabelas FROM pg_tables WHERE schemaname='industria';"

docker compose -f $ComposeFile exec -T db psql -U aluno -d pbl_industria_homologacao `
  -c "SELECT COUNT(*) AS movimentacoes FROM industria.movimentacoes;"
```

**Resultado esperado:** **12 tabelas** e **500.000 movimentações**. Se esses números não aparecerem, investigue a restauração antes de avançar.

Volte à pasta principal para seguir com o Python:

```powershell
Set-Location ..
```

# B. Caminho PostgreSQL instalado no Windows

## B1. Conferir a instalação local

Instale o PostgreSQL 18 para Windows, se ainda não estiver instalado, pelo instalador indicado em **postgresql.org/download/windows/**. Na instalação padrão, a conta administrativa se chama `postgres`. Se você configurou outro administrador, substitua o nome nos comandos abaixo.

Na **pasta principal do PBL**, execute:

```powershell
$PgBin = "C:\Program Files\PostgreSQL\18\bin"
$AdminUser = "postgres"  # altere se seu administrador possui outro nome
$PgPort = 5432  # ajuste se o PostgreSQL nativo usa outra porta

& "$PgBin\psql.exe" -h 127.0.0.1 -p $PgPort -U $AdminUser `
  -d postgres -c "SELECT current_user, version();"
```

O PowerShell pode solicitar a senha do administrador. Se não encontrar `psql.exe`, ajuste `$PgBin` para o local real da instalação. Se a porta 5432 já estiver sendo usada pelo Docker, interrompa um dos serviços ou configure uma porta alternativa de forma consistente.

## B2. Restaurar o dump e preparar o acesso

Na pasta principal do PBL, execute:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\configuracao\restaurar_pbl.ps1 -Modo Windows `
  -PgBin $PgBin -AdminUser $AdminUser -PgPort $PgPort
```

O comando cria o banco, restaura o dump e configura `pbl_app`. Quando solicitado, escolha e confirme a senha local da aplicação. Se a conta já existir na mesma instância, use a senha que ela já possui. Você vai informar essa senha na etapa C2.

Se o comando informar que o banco já existe, confira a instalação antes de prosseguir. Se houve uma falha depois da criação do banco, o banco pode ter ficado vazio. Consulte o professor antes de repetir a restauração.

## B3. Conferir o banco restaurado

```powershell
& "$PgBin\psql.exe" -h 127.0.0.1 -p $PgPort -U $AdminUser `
  -d pbl_industria_homologacao `
  -c "SELECT COUNT(*) AS tabelas FROM pg_tables WHERE schemaname='industria';"

& "$PgBin\psql.exe" -h 127.0.0.1 -p $PgPort -U $AdminUser `
  -d pbl_industria_homologacao `
  -c "SELECT COUNT(*) AS movimentacoes FROM industria.movimentacoes;"
```

**Resultado esperado:** **12 tabelas** e **500.000 movimentações**. Continue com a etapa C.

# C. Aplicação Python (comum aos dois caminhos)

## C1. Criar o ambiente virtual e instalar dependências

De volta à **pasta principal do PBL**, execute:

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\aplicacao\requirements.txt
```

O pacote utiliza as bibliotecas `psycopg` e `python-dotenv`. Use o Python do ambiente virtual em todos os comandos; **não é necessário ativar** a `.venv` no PowerShell.

## C2. Configurar a conexão

```powershell
Copy-Item .\aplicacao\.env.example .\aplicacao\.env
notepad .\aplicacao\.env
```

Preencha o arquivo `aplicacao/.env` conforme abaixo. Use **a senha que você definiu para `pbl_app`**, não a senha do administrador do banco.

```dotenv
PGHOST=127.0.0.1
PGPORT=5432
PGDATABASE=pbl_industria_homologacao
PGUSER=pbl_app
PGPASSWORD=SENHA_LOCAL_DO_PBL_APP
```

Se o PostgreSQL estiver em outra porta (por exemplo, 55432 no Docker), altere `PGPORT` para o valor correspondente. **Não envie o `.env` com credenciais ao professor nem publique em repositórios.**

Caso você tenha definido previamente variáveis `PGUSER`, `PGPASSWORD` ou `PGDATABASE` no PowerShell, elas podem substituir os valores do `.env`. Para conferir:

```powershell
Get-ChildItem Env:PG*
```

Se essas variáveis foram definidas apenas para testes anteriores e estão incorretas, remova-as **somente nesta sessão** antes de repetir o teste:

```powershell
Remove-Item Env:\PGUSER, Env:\PGPASSWORD, Env:\PGDATABASE -ErrorAction SilentlyContinue
```

## C3. Testes iniciais sem alterar dados

```powershell
.\.venv\Scripts\python.exe .\aplicacao\app.py verificar
.\.venv\Scripts\python.exe .\aplicacao\app.py estoques
.\.venv\Scripts\python.exe .\aplicacao\app.py componentes
.\.venv\Scripts\python.exe .\aplicacao\app.py custo --os OS-2026-001
```

O comando `verificar` deverá identificar o banco `pbl_industria_homologacao` e o usuário `pbl_app`. Os demais comandos permitem conhecer algumas funcionalidades existentes do sistema. **Registre o que foi observado, sem tentar corrigir os dados nesta etapa.**

Para utilizar o menu interativo:

```powershell
.\.venv\Scripts\python.exe .\aplicacao\app.py
```

**Atenção:** certas opções do menu alteram registros ou executam operações repetidas. Antes de realizar experimentos que modifiquem dados, preserve o dump original e trabalhe preferencialmente em uma cópia separada do banco.

# D. Conferência da instalação e início da investigação

Marque os itens antes de iniciar os relatos do cliente:

- [ ] PostgreSQL 18 acessível por Docker **ou** por instalação nativa.
- [ ] Banco `pbl_industria_homologacao` criado sem substituir outro banco.
- [ ] Dump restaurado sem erros.
- [ ] Schema `industria` com **12 tabelas**.
- [ ] Tabela `industria.movimentacoes` com **500.000 registros**.
- [ ] Conta `pbl_app` configurada com uma senha local.
- [ ] Python e dependências instalados na `.venv`.
- [ ] `app.py verificar` mostra `pbl_app` e o banco correto.
- [ ] Consultas iniciais funcionam sem alterar o banco.

**Registro mínimo de evidência:** guarde uma captura de tela com a contagem das tabelas e movimentações, outra com `app.py verificar` e um breve registro de qual ambiente foi escolhido (Docker ou Windows nativo). Não inclua senhas nas capturas.

A partir deste ponto, o trabalho passa à **investigação do sistema legado**. Os incidentes, hipóteses, experimentos e correções serão orientados pelo enunciado específico do PBL. Nenhuma solução está pressuposta neste guia de instalação.

# E. Problemas comuns de instalação

| Sintoma | Primeira verificação |
|---|---|
| `no configuration file provided` | Confira `$ComposeFile` e execute `docker compose -f $ComposeFile ...` na pasta `docker` do kit. |
| `database already exists` | A criação já foi executada. Não restaure novamente sobre a base existente; confira as contagens. |
| `password authentication failed` | Verifique qual conta está sendo usada (`aluno` ou `postgres` para preparar; `pbl_app` para a aplicação) e qual senha foi definida. |
| `role "pbl_app" does not exist` | Confira se a restauração da etapa A2 ou B2 terminou sem erros e se a aplicação aponta para a mesma instância. |
| `permission denied for schema industria` | Confira se a configuração de acesso foi aplicada **no banco restaurado**, com a conta administradora. |
| `ModuleNotFoundError: dotenv` | Execute a instalação a partir de `aplicacao/requirements.txt` usando o Python da `.venv`. |
| `connection refused` | Confirme se o PostgreSQL está iniciado, a porta está correta e o Docker/nativo não estão disputando `5432`. |
| `arquivo .dump não encontrado` | Confira se extraiu todo o ZIP e se `industria_homologacao_500k.dump` está na pasta principal, ao lado de `aplicacao`, `docker` e `configuracao`. |

## Referências de instalação

- PostgreSQL 18 - `pg_restore`: https://www.postgresql.org/docs/18/app-pgrestore.html
- PostgreSQL para Windows: https://www.postgresql.org/download/windows/
- Docker - PostgreSQL e volumes: https://docs.docker.com/guides/postgresql/

*Guia para ambiente didático local. Não reutilize estas credenciais nem esta configuração em produção.*
