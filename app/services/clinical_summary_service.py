"""
Serviço para geração de resumo clínico usando IA.

Analisa biomarcadores extraídos e gera insights clínicos estruturados:
- Resumo geral
- Alertas com severidade
- Recomendações
- Destilações (insights importantes)
- Próximos passos
"""

import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from google import genai
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.exame import Exame

logger = logging.getLogger(__name__)

PROMPT_CLINICAL_SUMMARY = """
Você é um assistente de análise clínica especializado em interpretar exames laboratoriais.
Analise os seguintes biomarcadores de um exame de sangue e forneça uma análise clínica estruturada.

BIOMARCADORES:
{biomarcadores_formatados}

Responda EM PORTUGUÊS em formato JSON com as seguintes chaves:

1. "resumo_geral": string - Visão geral dos resultados em 2-3 frases claras e objetivas

2. "alertas": lista de objetos - Cada objeto deve ter:
   - "biomarcador": nome do marcador
   - "valor": valor encontrado
   - "referencia": intervalo de referência
   - "severidade": "critico" (fora da referência por margem significativa), 
                   "atencao" (próximo aos limites), ou 
                   "normal" (dentro da referência)
   - "descricao": explicação clara do significado clínico

3. "recomendacoes": lista de strings - Ações práticas baseadas nos resultados

4. "destilacoes": lista de strings - Insights importantes que o paciente deve saber

5. "proximos_passos": lista de strings - Sugestões de acompanhamento médico

Exemplo de resposta:
{
  "resumo_geral": "O hemograma apresenta alterações nos leucócitos...",
  "alertas": [
    {
      "biomarcador": "LEUCÓCITOS",
      "valor": "12000",
      "referencia": "4000-10000",
      "severidade": "atencao",
      "descricao": "Leve leucocitose pode indicar processo inflamatório"
    }
  ],
  "recomendacoes": ["Acompanhamento com médico clínico geral"],
  "destilacoes": ["Os valores alterados podem ser temporários"],
  "proximos_passos": ["Repetir exame em 15 dias se sintomas persistirem"]
}

Responda APENAS com o JSON, sem markdown ou texto adicional.
"""


class ClinicalSummaryService:
    """Serviço para geração de resumos clínicos usando IA."""

    def __init__(self):
        self.client = None
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-2.0-flash"

    def _format_biomarkers(self, biomarcadores: list[dict]) -> str:
        """
        Formata lista de biomarcadores para o prompt.

        Args:
            biomarcadores: Lista de dicts com dados normalizados

        Returns:
            String formatada para o prompt
        """
        if not biomarcadores:
            return "Nenhum biomarcador disponível"

        lines = []
        for bm in biomarcadores:
            nome = bm.get(
                "nome_marcador_normalizado", bm.get("nome_marcador", "Desconhecido")
            )
            valor = bm.get("valor_extraido", "N/A")
            unidade = bm.get("unidade_medida_normalizada", bm.get("unidade_medida", ""))

            ref_min = bm.get("referencia_min")
            ref_max = bm.get("referencia_max")

            if ref_min is not None and ref_max is not None:
                referencia = f"{ref_min} - {ref_max} {unidade}".strip()
            elif ref_min is not None:
                referencia = f"> {ref_min} {unidade}".strip()
            elif ref_max is not None:
                referencia = f"< {ref_max} {unidade}".strip()
            else:
                referencia = bm.get("referencia_lab", "Não informada")

            status = bm.get("status_alerta", "indefinido")

            lines.append(
                f"• {nome}: {valor} {unidade} (Referência: {referencia}, Status: {status})".strip()
            )

        return "\n".join(lines)

    def _parse_response(self, text: str) -> dict | None:
        """
        Parse da resposta da IA para JSON.

        Args:
            text: Texto retornado pela IA

        Returns:
            Dict parseado ou None se falhar
        """
        try:
            # Early exit: text vazio
            if not text:
                logger.error("Resposta vazia da IA")
                return None

            # Remove markdown se presente
            cleaned = text.replace("```json", "").replace("```", "").strip()

            dados = json.loads(cleaned)

            # Fail Fast: validar estrutura obrigatória
            required_keys = [
                "resumo_geral",
                "alertas",
                "recomendacoes",
                "destilacoes",
                "proximos_passos",
            ]

            missing_keys = [k for k in required_keys if k not in dados]
            if missing_keys:
                logger.error(f"Resposta incompleta - chaves faltando: {missing_keys}")
                return None

            return dados

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear resposta JSON: {e}")
            return None

    async def generate_clinical_summary(
        self,
        db: Session,
        exame_id: UUID,
        biomarcadores: list[dict],
    ) -> dict[str, Any] | None:
        """
        Gera resumo clínico para um exame.

        Args:
            db: Sessão do banco
            exame_id: UUID do exame
            biomarcadores: Lista de biomarcadores normalizados

        Returns:
            Dict com resumo clínico ou None se falhar
        """
        if not self.client:
            logger.error("GEMINI_API_KEY não configurada - resumo clínico indisponível")
            return None

        # Early exit: sem biomarcadores
        if not biomarcadores:
            logger.warning(f"Sem biomarcadores para analisar no exame {exame_id}")
            return None

        # Operação de DB é bloqueante, rodar em thread
        loop = asyncio.get_event_loop()
        
        def get_exame_sync():
            return db.query(Exame).filter(Exame.id == exame_id).first()
        
        exame = await loop.run_in_executor(None, get_exame_sync)
        if not exame:
            logger.error(f"Exame {exame_id} não encontrado")
            return None

        if exame.clinical_summary:
            logger.info(f"Retornando resumo clínico cached para exame {exame_id}")
            return exame.clinical_summary

        try:
            # Formatar biomarcadores para prompt
            biomarcadores_text = self._format_biomarkers(biomarcadores)
            prompt = PROMPT_CLINICAL_SUMMARY.format(
                biomarcadores_formatados=biomarcadores_text
            )

            # Chamar IA (Async SDK)
            logger.info(f"Gerando resumo clínico para exame {exame_id} (Async)")
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[prompt],
            )

            # Parse da resposta
            summary = self._parse_response(response.text)
            if not summary:
                logger.error(f"Falha ao parsear resposta para exame {exame_id}")
                return None

            # Salvar no banco (bloqueante)
            def save_summary_sync():
                now = datetime.now(timezone.utc)
                stmt = (
                    update(Exame)
                    .where(Exame.id == exame_id)
                    .values(
                        clinical_summary=summary,
                        summary_generated_at=now,
                    )
                )
                db.execute(stmt)
                db.commit()
            
            await loop.run_in_executor(None, save_summary_sync)

            logger.info(
                f"Resumo clínico gerado para exame {exame_id} - "
                f"{len(summary.get('alertas', []))} alertas"
            )

            return summary

        except Exception as e:
            logger.exception(f"Erro ao gerar resumo clínico para exame {exame_id}: {e}")
            def rollback_sync():
                db.rollback()
            await loop.run_in_executor(None, rollback_sync)
            return None

    async def regenerate_summary(
        self,
        db: Session,
        exame_id: UUID,
        biomarcadores: list[dict],
    ) -> dict[str, Any] | None:
        """
        Força regeneração do resumo clínico.

        Args:
            db: Sessão do banco
            exame_id: UUID do exame
            biomarcadores: Lista de biomarcadores normalizados

        Returns:
            Dict com novo resumo clínico ou None se falhar
        """
        if not self.client:
            logger.error("GEMINI_API_KEY não configurada - resumo clínico indisponível")
            return None

        logger.info(f"Regenerando resumo clínico para exame {exame_id}")

        # Limpar resumo existente (bloqueante)
        loop = asyncio.get_event_loop()
        
        def clear_summary_sync():
            stmt = (
                update(Exame)
                .where(Exame.id == exame_id)
                .values(
                    clinical_summary=None,
                    summary_generated_at=None,
                )
            )
            db.execute(stmt)
            db.commit()
        
        await loop.run_in_executor(None, clear_summary_sync)

        # Gerar novo resumo
        return await self.generate_clinical_summary(db, exame_id, biomarcadores)
