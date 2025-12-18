from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from . import models, database, schemas
import shutil
import os
import uuid
from typing import List
from .services import ai_service
from datetime import datetime

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Sistema OCR Exames")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/pacientes/", response_model=schemas.PacienteCreate)
def create_paciente(paciente: schemas.PacienteCreate, db: Session = Depends(database.get_db)):
    db_paciente = db.query(models.Paciente).filter(models.Paciente.cpf == paciente.cpf).first()
    if db_paciente:
        raise HTTPException(status_code=400, detail="CPF já cadastrado")

    novo_paciente = models.Paciente(
        nome=paciente.nome,
        cpf=paciente.cpf,
        data_nascimento=paciente.data_nascimento,
        sexo_biologico=paciente.sexo_biologico
    )
    
    db.add(novo_paciente)
    db.commit()
    db.refresh(novo_paciente)
    return novo_paciente


@app.get("/pacientes/", response_model=List[schemas.PacienteResponse])
def list_pacientes(db: Session = Depends(database.get_db)):
    pacientes = db.query(models.Paciente).all()
    return pacientes


@app.get("/pacientes/{paciente_id}", response_model=schemas.PacienteResponse)
def get_paciente(paciente_id: uuid.UUID, db: Session = Depends(database.get_db)):
    paciente = db.query(models.Paciente).filter(models.Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    return paciente


@app.post("/pacientes/{paciente_id}/upload-exame/")
async def upload_exame(
    paciente_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    paciente = db.query(models.Paciente).filter(models.Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    # 2. Gerar um nome único para o arquivo para evitar sobrescrita
    file_extension = os.path.splitext(file.filename)[1]
    novo_nome_arquivo = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, novo_nome_arquivo)

    # 3. Salvar o arquivo no diretório 'uploads'
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 4. Criar o registro do exame no Banco de Dados
    novo_exame = models.Exame(
        paciente_id=paciente_id,
        url_documento=file_path,
        status_processamento="pendente" # Será alterado pelo OCR depois
    )

    db.add(novo_exame)
    db.commit()
    db.refresh(novo_exame)

    dados_extraidos = None 

    try:
        # 4. Chama a IA para extrair os dados
        dados_extraidos = ai_service.extrair_dados_exame(file_path)

        if "exame" in dados_extraidos:
            info_exame = dados_extraidos["exame"]
            novo_exame.laboratorio = info_exame.get("laboratorio")

            data_str = info_exame.get("data")
            if data_str:
                try:
                    novo_exame.data_coleta = datetime.strptime(data_str, "%Y-%m-%d").date()
                except:
                    pass
        
        # 5. Salva os biomarcadores
        for item in dados_extraidos['exame']['biomarcadores']:
            novo_resultado = models.ResultadoBiomarcador(
                exame_id=novo_exame.id,
                nome_marcador=item['nome'],
                valor_extraido=item['valor'],
                unidade_medida=item['unidade'],
                referencia_lab=item['referencia']
            )
            db.add(novo_resultado)
        
        novo_exame.status_processamento = "concluido"
        db.commit()
        
        return {"status": "sucesso", "exame_id": novo_exame.id, "dados": dados_extraidos}

    except Exception as e:
        novo_exame.status_processamento = "erro"
        db.commit()
        # Aqui lançamos um erro HTTP real para você ver o que a IA respondeu de errado
        raise HTTPException(status_code=500, detail=f"Erro na IA: {str(e)}")
    

@app.get("/exames/{exame_id}", response_model=schemas.DetalheExameResponse)
def get_detalhe_exame(exame_id: uuid.UUID, db: Session = Depends(database.get_db)):
    exame = db.query(models.Exame).filter(models.Exame.id == exame_id).first()
    
    if not exame:
        raise HTTPException(status_code=404, detail="Exame não encontrado")
        
    return exame