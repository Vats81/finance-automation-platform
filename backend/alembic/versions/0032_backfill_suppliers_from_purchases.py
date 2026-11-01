"""give every supplier already typed on a purchase a vendor record, and link the purchase to it

Revision ID: 0032
Revises: 0031
Create Date: 2026-11-02

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0032"
down_revision: Union[str, None] = "0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # One name-only vendor per business and supplier name (ignoring capitals and spacing), unless the
    # business already has a vendor of that name.
    op.execute(
        """
        INSERT INTO vendors (id, legal_name, contact_email, tax_id, street, city, state, postal_code,
                             country, status, business_id)
        SELECT gen_random_uuid(), min(btrim(p.vendor_name)), '', '', '', '', '', '', 'US', 'pending_review',
               p.business_id
        FROM purchases p
        WHERE p.vendor_id IS NULL AND p.vendor_name IS NOT NULL AND btrim(p.vendor_name) <> ''
          AND NOT EXISTS (
              SELECT 1 FROM vendors v
              WHERE v.business_id = p.business_id AND lower(btrim(v.legal_name)) = lower(btrim(p.vendor_name))
          )
        GROUP BY p.business_id, lower(btrim(p.vendor_name))
        """
    )
    op.execute(
        """
        UPDATE purchases p SET vendor_id = v.id
        FROM vendors v
        WHERE p.vendor_id IS NULL AND p.vendor_name IS NOT NULL AND btrim(p.vendor_name) <> ''
          AND v.business_id = p.business_id AND lower(btrim(v.legal_name)) = lower(btrim(p.vendor_name))
        """
    )


def downgrade() -> None:
    # The vendors are real records by now (they may have been edited); nothing is removed.
    pass
