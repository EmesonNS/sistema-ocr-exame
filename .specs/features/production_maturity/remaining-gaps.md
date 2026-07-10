# Remaining Gaps: OCR Production Readiness

## Leitura Executiva

O backend OCR já cobre a maior parte do núcleo produtivo: extração, infraestrutura de avaliação, FHIR, LOINC dinâmico, auditoria visual, retenção e observabilidade de custo. O que ainda impede a leitura honesta de "100% production-ready" é a maturidade da integração de produto, a implementação real do frontend de auditoria, a validação com segredos reais, a operação observável em ambiente de produção e a qualidade clínica medida por reports versionados.

## Gaps Priorizados

### P0 - Integração entre produto e OCR

Origem:
- A decisão arquitetural separou o OCR como serviço privado, consumido apenas pelo `storge-service`.
- O contrato público principal de upload, status, listagem, detalhe e download já está materializado no `storge-app`; recursos avançados como resumo clínico, auditoria visual, FHIR e verificação humana ainda não estão plenamente expostos como jornada de produto.

Por que importa:
- Sem maturar essa ponte, o OCR fica tecnicamente forte, mas parte das capacidades internas permanece invisível ou subutilizada no produto.
- O risco não é só de "integração pendente"; é de o produto consumir apenas um subconjunto do OCR, com semântica incompleta de auditoria, qualidade e suporte.

Melhor resolução:
- Manter formalizado o contrato de integração privada entre backend do produto e OCR.
- Expandir o proxy autenticado no backend do produto para recursos avançados quando fizerem parte da jornada.
- Garantir que upload, status, polling, download, resumo, auditoria e evidências tenham contrato público coerente quando expostos ao produto.

Tasks:
- Revisar mapa de rotas públicas e internas já existente.
- Validar que a autenticação do proxy continua restrita ao backend.
- Validar upload de exame, acompanhamento de processamento, download e retorno de erro.
- Planejar exposição de resumo/auditoria/evidência/FHIR sem chamar o OCR diretamente pela UI.

Critério de aceite:
- O OCR não é acessado diretamente pela interface pública.
- O backend do produto consegue subir exame, acompanhar processamento e recuperar o arquivo original com contrato estável.
- Recursos avançados são marcados como internos ou expostos formalmente, sem ambiguidade documental.

### P0 - Frontend de auditoria

Origem:
- O app frontend existe em `storge-app/storge-system` e já cobre upload, polling, histórico e resultado resumido de exames.
- A jornada completa de auditoria clínica ainda não está materializada na UI: evidência visual por biomarcador, verificação humana, inspeção FHIR/LOINC e revisão operacional ficam disponíveis no OCR/backend, mas não como fluxo completo de produto.

Por que importa:
- A auditoria humana é parte do fluxo clínico e operacional.
- Sem tela real de auditoria, a verificação humana fica tecnicamente disponível, mas inutilizável para operação diária.

Melhor resolução:
- Implementar o dashboard no frontend do produto existente.
- Consumir exclusivamente as APIs públicas já expostas pelo backend.
- Tratar lista, detalhe, crop, status, FHIR e verify como uma única jornada de auditoria.

Tasks:
- Criar shell do app e rota do dashboard.
- Implementar lista operacional com paginação e filtros.
- Implementar detalhe do exame e estados de carregamento/erro.
- Implementar visualização da evidência por biomarcador.
- Implementar ação de verificação humana com feedback imediato.
- Incluir inspeção do Bundle FHIR.

Critério de aceite:
- Um auditor localiza um exame, abre a evidência, valida o resultado e marca o biomarcador como verificado sem sair da interface.

### P0 - Validação de produção com segredos reais

Origem:
- O stack já tem checagens de readiness, mas o ambiente final ainda precisa de confirmação com segredos reais e deploy efetivo.

Por que importa:
- Sem essa etapa, há risco de confundir ambiente saudável com ambiente apenas configurado.

Melhor resolução:
- Rodar a sequência de validação final no VPS com segredos reais.
- Confirmar banco, Redis, worker, storage e rotas públicas.

Tasks:
- Executar inspeção read-only do host antes de qualquer mudança.
- Validar secrets, banco, Redis e worker.
- Confirmar variáveis de storage e rede de produção.
- Fazer deploy controlado e smoke pós-deploy.

Critério de aceite:
- O ambiente sobe com segredos reais e smoke funcional de ponta a ponta.

### P1 - Observabilidade e operação contínua

Origem:
- Há benchmark, métricas de custo e retenção, mas ainda falta ciclo operacional completo de monitoramento.

Por que importa:
- Um sistema clínico pode estar correto em teste e degradar em uso real sem alerta útil.

Melhor resolução:
- Adicionar monitoramento contínuo de qualidade, falhas e custos.
- Registrar regressões de OCR, falhas de evidência e quedas de throughput.

Tasks:
- Definir indicadores mínimos de operação.
- Criar alertas para falha de processamento, aumento de erro e degradação de custo.
- Rodar amostragem periódica de exames reais.
- Atualizar a baseline da knowledge layer quando houver drift clínico.

Critério de aceite:
- O time consegue perceber regressão antes de o usuário final acumular falhas.

## Relação com a Situação Atual

- Já concluído como infraestrutura: OCR eval, knowledge layer, FHIR DiagnosticReport, LOINC dinâmico, retenção, observabilidade de custo e auditoria de backend.
- Já materializado no produto: upload/status/listagem/detalhe/download via backend Storge, com OCR privado.
- Ainda aberto como maturidade: qualidade clínica de release medida por reports versionados, frontend real de auditoria, rollout com segredos reais e monitoramento contínuo.
