"""Performance benchmarks for document service operations."""

import pytest
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.models.document import DocumentCreate
from app.services import document as document_service
from app.services import association as association_service


@pytest.fixture(name="document_setup_data")
def document_setup_fixture(
    session: Session,
    user_create_data_factory,
    association_create_data_factory,
):
    """Setup an association for document creation benchmarks."""
    association = association_service.create_association(
        session=session,
        user_in=user_create_data_factory(),
        association_in=association_create_data_factory(),
    )
    session.flush()
    return {"id_asso": association.id_asso}


def test_document_creation_performance(
    benchmark: BenchmarkFixture, session: Session, document_setup_data, tracker
):
    """Benchmark document creation operation."""

    @benchmark
    def create_document():
        document_in = DocumentCreate(
            doc_name="Bench Doc",
            url_doc="https://example.com/bench.pdf",
            id_asso=document_setup_data["id_asso"],
        )
        document = document_service.create_document(
            session=session,
            document_in=document_in,
            association_id=document_setup_data["id_asso"],
        )
        tracker.append(document)
        return document.id_doc


def test_get_document_performance(
    benchmark: BenchmarkFixture, session: Session, document_setup_data
):
    """Benchmark document retrieval by ID operation."""
    document_in = DocumentCreate(
        doc_name="Bench Doc",
        url_doc="https://example.com/bench.pdf",
        id_asso=document_setup_data["id_asso"],
    )
    document = document_service.create_document(
        session=session,
        document_in=document_in,
        association_id=document_setup_data["id_asso"],
    )
    session.flush()
    document_id = document.id_doc

    @benchmark
    def get_document():
        session.expire_all()
        assert document_id is not None
        return document_service.get_document(session=session, document_id=document_id)


def test_get_pending_documents_performance(
    benchmark: BenchmarkFixture, session: Session, document_setup_data
):
    """Benchmark retrieving a list of pending documents."""
    # Setup: Create some pending documents
    for i in range(10):
        document_in = DocumentCreate(
            doc_name=f"Bench Doc {i}",
            url_doc=f"https://example.com/bench{i}.pdf",
            id_asso=document_setup_data["id_asso"],
        )
        document_service.create_document(
            session=session,
            document_in=document_in,
            association_id=document_setup_data["id_asso"],
        )
    session.flush()

    @benchmark
    def get_pending():
        session.expire_all()
        return document_service.get_pending_documents(session=session)
