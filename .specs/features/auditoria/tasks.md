# Tasks: Phase 8 (Visual Audit)

## T26: Evidence Rendering [P]
- [x] Implementar \`app/services/evidence_service.py\` para processar crops de PDF/Imagem.
- [x] Criar endpoint \`GET /exames/{id}/resultados/{res_id}/evidence\` em \`app/api/endpoints/exames.py\`.
- [x] Implementar cache de crops no Redis para evitar re-processamento de PDF.
- **Done when:** Uma chamada ao endpoint retorna o trecho exato do PDF onde o valor está localizado.

## T27: Audit Workflow
- [x] Adicionar campo \`is_human_verified\` (Boolean) ao modelo \`ResultadoBiomarcador\`.
- [x] Criar endpoint \`POST /exames/{id}/resultados/{res_id}/verify\` para marcar como auditado.
- [x] Gerar e rodar migração \`007_add_audit_fields\`.
- **Done when:** Biomarcadores podem ser marcados como "Verificados" via API.

## T28: UI Prototype (Mockup)
- [x] Documentar especificações para o dashboard de auditoria (Frontend requirements).
- [x] Criar protótipo estático de referência em `docs/auditoria-dashboard-prototipo.html`.
- [ ] Implementar o dashboard real no repo frontend do produto.
