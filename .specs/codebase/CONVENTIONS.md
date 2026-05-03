# Coding Conventions

## Geral
- **Linguagem:** Python 3.10+
- **Estilo:** Seguir padrões de Clean Code e PEP 8.
- **Idioma:** Código e comentários internos em Português (PT-BR) conforme preferência do projeto.

## Padrões de Implementação
- **Early Exit:** Sair de funções o mais rápido possível em casos de erro/vazio.
- **Parse, Don't Validate:** Preferir transformar o dado em um tipo forte (Pydantic) em vez de apenas checar flags.
- **Non-blocking I/O:** Todas as chamadas de rede ou DB em rotas API devem ser assíncronas. Operações síncronas pesadas devem usar `run_in_executor`.

## Banco de Dados
- **Atomicidade:** Incrementos e mudanças de status críticas devem ser feitas no nível do banco (SQL update) para evitar Race Conditions.
- **Migrations:** Nunca alterar o schema sem criar uma nova migração Alembic.

## Testes
- **TDD:** Escrever testes de comportamento antes da implementação de novas features.
- **Isolamento:** Cada teste deve limpar seu estado no DB (metodologia do `conftest.py` atual).
