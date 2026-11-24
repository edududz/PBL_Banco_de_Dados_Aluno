# PBL Banco de Dados - kit de validação da instalação

Este pacote contém a **aplicação inicial**, a configuração de ambiente e um guia de instalação para as alternativas PostgreSQL 18 em Docker ou instalado no Windows.

O arquivo `industria_homologacao_500k.dump` **já vem no ZIP**, na raiz do kit. A cópia de referência possui 500.000 linhas em `industria.movimentacoes` e 12 tabelas no schema `industria`.

Comece pelo documento `tutorial/GUIA_Estudante_PBL_PostgreSQL.pdf` (ou pela versão editável `.docx`). Escolha **apenas um** ambiente PostgreSQL: Docker **ou** Windows nativo.

**Atenção:** este material não contém a resolução dos incidentes. A etapa inicial consiste em restaurar o banco e verificar o funcionamento da aplicação, preservando o estado original dos dados.

Nunca entregue arquivos `.env` contendo senhas a outras pessoas. Não apague volumes de bancos existentes para corrigir falhas de instalação.
