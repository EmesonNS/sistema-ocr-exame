#!/usr/bin/env python3
"""
Script CLI para criar API Keys iniciais.
Uso: python scripts/create_api_key.py <client_name>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.api_key import ApiKey
from app.core.auth import hash_api_key
import secrets


def create_api_key(client_name: str, rate_limit: int = 60):
    """Cria uma nova API Key e imprime na tela."""
    raw_key = secrets.token_hex(32)
    key_hash = hash_api_key(raw_key)

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Verifica se já existe
        existing = db.query(ApiKey).filter(ApiKey.client_name == client_name).first()
        if existing:
            print(f"⚠️  Já existe uma API Key para '{client_name}'")
            return

        api_key = ApiKey(
            key_hash=key_hash,
            client_name=client_name,
            rate_limit_per_minute=rate_limit,
            is_active=True
        )
        db.add(api_key)
        db.commit()

        print(f"✅ API Key criada com sucesso!")
        print(f"\n{'='*60}")
        print(f"Client: {client_name}")
        print(f"API Key: {raw_key}")
        print(f"{'='*60}\n")
        print("⚠️  Guarde esta chave com segurança. Ela não será exibida novamente.")
        print(f"\nPara usar no curl:")
        print(f'curl -H "X-API-Key: {raw_key}" http://localhost:8001/api/v1/patients/1/exames')

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/create_api_key.py <nome_do_cliente> [rate_limit]")
        print("Exemplo: python scripts/create_api_key.py storge-backend 120")
        sys.exit(1)

    client_name = sys.argv[1]
    rate_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 60

    create_api_key(client_name, rate_limit)
