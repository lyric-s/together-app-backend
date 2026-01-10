"""Category service module for CRUD operations."""

from sqlmodel import Session, select

from app.models.category import Category, CategoryCreate, CategoryUpdate
from app.exceptions import NotFoundError, AlreadyExistsError


def get_all_categories(session: Session) -> list[Category]:
    """
    Retrieve all categories.

    Parameters:
        session: Database session.

    Returns:
        list[Category]: All categories ordered alphabetically by label.
    """
    statement = select(Category).order_by(Category.label)
    return list(session.exec(statement).all())


def get_category(session: Session, category_id: int) -> Category | None:
    """
    Retrieve a category by ID.

    Parameters:
        session: Database session.
        category_id: The category's primary key.

    Returns:
        Category | None: The category or None if not found.
    """
    return session.get(Category, category_id)


def create_category(session: Session, category_in: CategoryCreate) -> Category:
    """
    Create a new category.

    Parameters:
        session: Database session.
        category_in: Category creation data.

    Returns:
        Category: The created category.

    Raises:
        AlreadyExistsError: If a category with the same label already exists.
    """
    # Check if category with same label exists
    existing = session.exec(
        select(Category).where(Category.label == category_in.label)
    ).first()
    if existing:
        raise AlreadyExistsError("Category", "label", category_in.label)

    category = Category.model_validate(category_in)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def update_category(
    session: Session, category_id: int, category_update: CategoryUpdate
) -> Category:
    """
    Update a category.

    Parameters:
        session: Database session.
        category_id: The category's primary key.
        category_update: Update data.

    Returns:
        Category: The updated category.

    Raises:
        NotFoundError: If the category doesn't exist.
        AlreadyExistsError: If updating to a label that already exists.
    """
    category = get_category(session, category_id)
    if not category:
        raise NotFoundError("Category", category_id)

    # Check if new label conflicts with existing category
    if category_update.label:
        existing = session.exec(
            select(Category).where(
                Category.label == category_update.label,
                Category.id_categ != category_id,
            )
        ).first()
        if existing:
            raise AlreadyExistsError("Category", "label", category_update.label)

    update_data = category_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def delete_category(session: Session, category_id: int) -> None:
    """
    Delete a category.

    Note: This will fail if any missions are still using this category
    due to foreign key constraints in the mission_category junction table.

    Parameters:
        session: Database session.
        category_id: The category's primary key.

    Raises:
        NotFoundError: If the category doesn't exist.
    """
    category = get_category(session, category_id)
    if not category:
        raise NotFoundError("Category", category_id)

    session.delete(category)
    session.commit()
