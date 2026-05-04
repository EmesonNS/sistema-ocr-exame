# Feature: Dashboard de Auditoria e Evidência Visual (Phase 8)

Fornecer transparência total e capacidade de conferência humana para o processo de extração.

## Requirements

### R23: Evidence Crop API
- O sistema MUST fornecer um endpoint para recuperar o recorte (crop) da imagem original associado a um biomarcador.
- O recorte deve usar as coordenadas `bounding_box` e `page_number` salvas.
- Traceability: `AUDIT-001`

### R24: Audit Status Tracking
- O modelo `ResultadoBiomarcador` SHOULD ter um campo para indicar se foi revisado por um humano.
- Traceability: `AUDIT-002`

### R25: Visual Citation Cache
- Para otimizar a performance, os recortes de evidência podem ser cacheados no Redis ou storage.
- Traceability: `AUDIT-003`
