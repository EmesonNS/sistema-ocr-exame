from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
    Query,
    Path,
    Header,
)
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, Any, cast
from datetime import datetime

from app.core.database import get_db
from app.services.exame_service import ExameService
from app.services.clinical_summary_service import ClinicalSummaryService
from app.schemas.exame import (
    ExameResponse,
    DetalheExameResponse,
    ExameListResponse,
    ExameStatusResponse,
    ClinicalSummaryResponse,
)
from app.core.auth import verify_api_key

router = APIRouter()
exame_service = ExameService()


@router.post(
    "/patients/{patient_id}/exames/upload",
    response_model=ExameResponse,
    summary="Upload de exame (PDF)",
    description=(
        "Faz upload de um arquivo PDF de exame laboratorial para um paciente. "
        "O arquivo é salvo e uma task assíncrona é disparada para extrair "
        "biomarcadores via IA. O exame inicia com status `pendente`."
    ),
    responses={
        200: {"description": "Exame criado e processamento iniciado"},
        400: {"description": "Arquivo não é PDF"},
        401: {"description": "API Key ausente ou inválida"},
    },
)
def upload_exame(
    patient_id: int = Path(..., description="ID do paciente no Storge", example=42),
    user_id: int = Query(..., description="ID do usuário que está fazendo o upload"),
    file: UploadFile = File(..., description="Arquivo PDF do exame laboratorial"),
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_api_key),
):
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Apenas arquivos PDF são permitidos"
        )

    return exame_service.processar_upload(db, patient_id, user_id, file)


@router.get(
    "/patients/{patient_id}/exames",
    response_model=ExameListResponse,
    summary="Listar exames de um paciente",
    description=(
        "Retorna uma lista paginada de todos os exames de um paciente. "
        "Use `page` e `limit` para navegação."
    ),
    responses={
        200: {"description": "Lista paginada de exames"},
        401: {"description": "API Key ausente ou inválida"},
    },
)
def list_exames(
    patient_id: int = Path(..., description="ID do paciente no Storge", example=42),
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_api_key),
):
    return exame_service.list_by_patient(db, patient_id, page, limit)


@router.get(
    "/exames/{exame_id}",
    response_model=DetalheExameResponse,
    summary="Detalhes de um exame",
    description=(
        "Retorna os detalhes completos de um exame incluindo todos os "
        "biomarcadores extraídos pelo OCR."
    ),
    responses={
        200: {"description": "Detalhes do exame com biomarcadores"},
        401: {"description": "API Key ausente ou inválida"},
        404: {"description": "Exame não encontrado"},
    },
)
def get_exame_details(
    exame_id: UUID = Path(..., description="UUID do exame"),
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_api_key),
):
    exame = exame_service.get_exame(db, exame_id)
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado")
    return exame


@router.get(
    "/exames/{exame_id}/status",
    response_model=ExameStatusResponse,
    summary="Status de processamento (polling)",
    description=(
        "Endpoint leve para polling do status de processamento de um exame. "
        "Retorna informações de progresso detalhadas incluindo estágio atual, "
        "percentual e mensagem descritiva. "
        "Valores possíveis para status: `pendente`, `processando`, `concluido`, `erro`. "
        "Valores possíveis para stage: `queued`, `downloading`, `ocr_extracting`, "
        "`ai_analyzing`, `normalizing`, `completed`, `failed`. "
        "Recomendamos polling a cada 3-5 segundos."
    ),
    responses={
        200: {"description": "Status atual do processamento"},
        401: {"description": "API Key ausente ou inválida"},
        404: {"description": "Exame não encontrado"},
    },
)
def get_exame_status(
    exame_id: UUID = Path(..., description="UUID do exame"),
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_api_key),
):
    exame: Any = exame_service.get_exame(db, exame_id)
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado")

    status = cast(str, exame.status_processamento)
    stage = cast(Optional[str], exame.processing_stage)
    percent = cast(Optional[int], exame.processing_percent)
    message = cast(Optional[str], exame.processing_message)
    has_summary = cast(bool, exame.clinical_summary is not None)
    return ExameStatusResponse(
        status=status,
        processing_stage=stage,
        processing_percent=percent,
        processing_message=message,
        has_summary=has_summary,
    )


# ========================================
# Clinical Summary Endpoints
# ========================================

clinical_summary_service = ClinicalSummaryService()


@router.get(
    "/exames/{exame_id}/resumo",
    response_model=ClinicalSummaryResponse,
    summary="Resumo clínico do exame",
    description=(
        "Retorna o resumo clínico gerado pela IA para o exame. "
        "Inclui: visão geral, alertas com severidade, recomendações, "
        "insights (destilações) e próximos passos. "
        "O resumo é cached após a primeira geração."
    ),
    responses={
        200: {"description": "Resumo clínico do exame"},
        401: {"description": "API Key ausente ou inválida"},
        404: {"description": "Exame não encontrado ou sem resumo"},
    },
)
async def get_clinical_summary(
    exame_id: UUID = Path(..., description="UUID do exame"),
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_api_key),
):
    exame: Any = exame_service.get_exame(db, exame_id)
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado")

    status_processamento = cast(str, exame.status_processamento)

    # Early exit: exame não concluído
    if status_processamento != "concluido":
        raise HTTPException(
            status_code=400,
            detail="Exame ainda está sendo processado",
        )

    # Early exit: sem biomarcadores
    resultados = list(getattr(exame, "resultados", []) or [])
    if len(resultados) == 0:
        raise HTTPException(
            status_code=404,
            detail="Exame não possui biomarcadores extraídos",
        )

    # Formatar biomarcadores para o serviço
    biomarcadores = [
        {
            "nome_marcador_normalizado": r.nome_marcador,
            "valor_extraido": r.valor_extraido,
            "unidade_medida_normalizada": r.unidade_medida,
            "referencia_min": float(r.referencia_min) if r.referencia_min else None,
            "referencia_max": float(r.referencia_max) if r.referencia_max else None,
            "referencia_lab": r.referencia_lab,
            "status_alerta": r.status_alerta,
        }
        for r in resultados
    ]

    summary = await clinical_summary_service.generate_clinical_summary(
        db, exame_id, biomarcadores
    )

    db.refresh(exame)

    if not summary:
        raise HTTPException(
            status_code=500,
            detail="Falha ao gerar resumo clínico",
        )

    return ClinicalSummaryResponse(
        resumo_geral=summary.get("resumo_geral", ""),
        alertas=summary.get("alertas", []),
        recomendacoes=summary.get("recomendacoes", []),
        destilacoes=summary.get("destilacoes", []),
        proximos_passos=summary.get("proximos_passos", []),
        generated_at=cast(Optional[datetime], exame.summary_generated_at),
    )


@router.post(
    "/exames/{exame_id}/resumo/regenerate",
    response_model=ClinicalSummaryResponse,
    summary="Regenerar resumo clínico",
    description=(
        "Força a regeneração do resumo clínico do exame. "
        "Útil quando o resumo anterior não foi satisfatório "
        "ou quando houver correções nos biomarcadores."
    ),
    responses={
        200: {"description": "Novo resumo clínico gerado"},
        401: {"description": "API Key ausente ou inválida"},
        404: {"description": "Exame não encontrado"},
    },
)
async def regenerate_clinical_summary(
    exame_id: UUID = Path(..., description="UUID do exame"),
    db: Session = Depends(get_db),
    authenticated: bool = Depends(verify_api_key),
):
    exame: Any = exame_service.get_exame(db, exame_id)
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado")

    status_processamento = cast(str, exame.status_processamento)

    # Early exit: exame não concluído
    if status_processamento != "concluido":
        raise HTTPException(
            status_code=400,
            detail="Exame ainda está sendo processado",
        )

    # Early exit: sem biomarcadores
    resultados = list(getattr(exame, "resultados", []) or [])
    if len(resultados) == 0:
        raise HTTPException(
            status_code=404,
            detail="Exame não possui biomarcadores extraídos",
        )

    # Formatar biomarcadores para o serviço
    biomarcadores = [
        {
            "nome_marcador_normalizado": r.nome_marcador,
            "valor_extraido": r.valor_extraido,
            "unidade_medida_normalizada": r.unidade_medida,
            "referencia_min": float(r.referencia_min) if r.referencia_min else None,
            "referencia_max": float(r.referencia_max) if r.referencia_max else None,
            "referencia_lab": r.referencia_lab,
            "status_alerta": r.status_alerta,
        }
        for r in resultados
    ]

    summary = await clinical_summary_service.regenerate_summary(
        db, exame_id, biomarcadores
    )

    if not summary:
        raise HTTPException(
            status_code=500,
            detail="Falha ao regenerar resumo clínico",
        )

    # Recarregar exame para obter novo timestamp
    db.refresh(exame)

    return ClinicalSummaryResponse(
        resumo_geral=summary.get("resumo_geral", ""),
        alertas=summary.get("alertas", []),
        recomendacoes=summary.get("recomendacoes", []),
        destilacoes=summary.get("destilacoes", []),
        proximos_passos=summary.get("proximos_passos", []),
        generated_at=cast(Optional[datetime], exame.summary_generated_at),
    )
