import pytest
import threading
from app.repositories.exame_repo import ExameRepository
from app.models.exame import ExameBatch

def test_batch_update_race_condition(db_session):
    """
    Simula múltiplos workers atualizando o mesmo lote simultaneamente.
    Se a atualização não for atômica, haverá perda de contagem.
    """
    repo = ExameRepository()
    
    # 1. Arrange: Criar um lote com 50 arquivos
    total_workers = 20
    batch = repo.create_batch(db_session, patient_id=1, total_files=total_workers)
    batch_id = batch.id
    db_session.expunge_all() # Limpar cache da sessão
    
    def worker_task():
        # Cada worker abre sua própria conexão usando o factory de teste
        from app.tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        try:
            repo.update_batch_progress(db, batch_id, success=True)
        finally:
            db.close()

    # 2. Act: Disparar múltiplos threads simultâneos
    threads = []
    for _ in range(total_workers):
        t = threading.Thread(target=worker_task)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # 3. Assert: Verificar se a contagem final está correta
    db_session.expire_all()
    final_batch = repo.get_batch(db_session, batch_id)
    
    print(f"\nResultado da Concorrência: {final_batch.completed_files}/{total_workers}")
    
    # Se houver bug de corrida, completed_files será < total_workers
    assert final_batch.completed_files == total_workers, \
        f"Race Condition detectada! Esperado {total_workers}, obtido {final_batch.completed_files}"
