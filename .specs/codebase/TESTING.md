# Testing Strategy

## Framework
- **Pytest** é a ferramenta padrão.
- Testes localizados em `app/tests/`.

## Categorias de Testes
1. **Unitários:** Focados em `biomarker_normalization` (lógica pura).
2. **Integração API:** Testam endpoints reais simulando o banco de dados.
3. **Segurança:** Validam Guardrails e injeção de prompt.
4. **Concorrência:** Testes específicos para Race Conditions (ex: `test_concurrency.py`).
5. **Rastreabilidade e Agentic Loop:** Validam extração de coordenadas 2D e re-inspeção por zoom.
6. **Interoperabilidade:** Validam mapeamento LOINC e serialização FHIR R4.

## Mocks
- IA e Webhooks externos **devem** ser mockados usando `unittest.mock.patch` e `AsyncMock`.
- Imagens e PDFs são simulados para evitar dependências de sistema no ambiente de CI.
