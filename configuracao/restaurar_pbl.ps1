[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Docker', 'Windows')]
    [string] $Modo,

    [string] $ComposeFile,
    [string] $PgBin = 'C:\Program Files\PostgreSQL\18\bin',
    [string] $AdminUser,
    [ValidateRange(1, 65535)]
    [int] $PgPort = 5432
)

$ErrorActionPreference = 'Stop'
$banco = 'pbl_industria_homologacao'
$dump = Join-Path (Split-Path -Parent $PSScriptRoot) 'industria_homologacao_500k.dump'
$acesso = Join-Path $PSScriptRoot '00_configurar_acesso.sql'
if (!(Test-Path -LiteralPath $dump -PathType Leaf)) {
    throw "Confira se extraiu todo o ZIP e se industria_homologacao_500k.dump esta na raiz do kit."
}

function Invoke-PblCommand {
    param([string] $Executavel, [string[]] $Argumentos)

    & $Executavel @Argumentos
    if ($LASTEXITCODE -ne 0) {
        throw "A etapa do comando $Executavel falhou (codigo $LASTEXITCODE)."
    }
}

$temporario = 'pbl-restauracao-' + [guid]::NewGuid().ToString('N')
if ($Modo -eq 'Docker') {
    if (!$ComposeFile) {
        throw 'Informe -ComposeFile com o caminho do Compose que foi iniciado.'
    }
    if (!$AdminUser) { $AdminUser = 'aluno' }
    $ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path
    $compose = @('compose', '-f', $ComposeFile)
    $cli = 'docker'
    $restaurar = $compose + @('exec', '-T', 'db', 'pg_restore')
    $criar = $compose + @('exec', '-T', 'db', 'psql')
    $psql = $compose + @('exec', 'db', 'psql')
    $pasta = "/tmp/$temporario"
    $dumpRemoto = "$pasta/base.dump"
    $sqlRestauracao = "$pasta/base.sql"
    $sqlAcesso = "$pasta/acesso.sql"
    Invoke-PblCommand $cli ($compose + @('exec', '-T', 'db', 'mkdir', $pasta))
} else {
    if (!$AdminUser) { $AdminUser = 'postgres' }
    $conexao = @('-h', '127.0.0.1', '-p', "$PgPort")
    $restaurar = @()
    $criar = $conexao
    $psql = $conexao
    $pasta = Join-Path ([System.IO.Path]::GetTempPath()) $temporario
    $dumpRemoto = $dump
    $sqlRestauracao = Join-Path $pasta 'base.sql'
    $sqlAcesso = $acesso
    New-Item -ItemType Directory -Path $pasta | Out-Null
}

try {
    if ($Modo -eq 'Docker') {
        Invoke-PblCommand $cli ($compose + @('cp', $dump, "db:$dumpRemoto"))
        Invoke-PblCommand $cli ($compose + @('cp', $acesso, "db:$sqlAcesso"))
        $pgRestoreExe = $psqlExe = $cli
    } else {
        $pgRestoreExe = Join-Path $PgBin 'pg_restore.exe'

        $psqlExe = Join-Path $PgBin 'psql.exe'
    }

    Invoke-PblCommand $pgRestoreExe ($restaurar + @(
        '--no-owner', '--no-acl', '--file', $sqlRestauracao, $dumpRemoto
    ))

    # A criacao falha antes de restaurar se o banco ja existir.
    Invoke-PblCommand $psqlExe ($criar + @('-X', '-q', '-U', $AdminUser, '-d', 'postgres', '-v', 'ON_ERROR_STOP=1',
        '-c', "CREATE DATABASE $banco TEMPLATE template0 ENCODING 'UTF8'"))
    Write-Host 'Restaurando o banco e configurando pbl_app. Informe a senha local quando solicitada.'
    Invoke-PblCommand $psqlExe ($psql + @(
        '-X', '-q', '-U', $AdminUser, '-d', $banco, '--single-transaction',
        '-v', 'ON_ERROR_STOP=1', '-v', 'restauracao_interativa=1',
        '-f', $sqlRestauracao, '-f', $sqlAcesso
    ))
    Write-Host "Restauracao concluida. Banco: $banco. Conta da aplicacao: pbl_app."
} finally {
    if ($Modo -eq 'Docker') {
        & $cli @compose exec -T db rm -f $dumpRemoto $sqlRestauracao $sqlAcesso
        & $cli @compose exec -T db rmdir $pasta
    } else {
        Remove-Item -LiteralPath $sqlRestauracao -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $pasta -ErrorAction SilentlyContinue
    }
}
