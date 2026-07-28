from app.identity.api.dependencies import require_role
from app.identity.domain.value_objects import Role

require_po_writer = require_role(Role.AP_CLERK, Role.FINANCE_ADMIN)
