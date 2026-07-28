"""Extension point, not wired in the foundation slice.

A true 3-way match reconciles Invoice + PurchaseOrder + a goods-receipt/
receiving record, which requires a Receiving bounded context that doesn't
exist yet (tracked in PHASE2_ROADMAP.md). Once that context lands, this
module would mirror two_way_match.py's TwoWayMatchService shape, taking a
third aggregate (GoodsReceipt) and additionally verifying received quantity
against both invoiced and ordered quantity before a match is accepted.
"""
