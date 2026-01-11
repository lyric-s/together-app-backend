from app.models.document import Document

d = Document(doc_name="test", url_doc="u", id_asso=1)
print(f"Has id_document: {hasattr(d, 'id_document')}")
print(f"id_document value: {d.id_document}")
