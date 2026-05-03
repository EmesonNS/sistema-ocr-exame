# Testing Strategy

## Framework
- **Pytest** é a ferramenta padrão.
- Testes localizados em `app/tests/`.

## Categorias de Testes
1. **Unitários:** Focados em `biomarker_normalization` (lógica pura).
2. **Integração API:** Testam endpoints reais simulando o banco de dados.
3. **Segurança:** Validam Guardrails e injeção de prompt.
4. **Concorrência:** Testes específicos para Race Conditions (ex: `test_concurrency.py`).

## Mocks
- IA e Webhooks externos **devem** ser mockados usando `unittest.mock.patch` e `AsyncMock` para garantir testes rápidos e determinísticos.
- O banco de dados de teste é um SQLite local ou PostgreSQL efêmero criado pelo `conftest.py`.
