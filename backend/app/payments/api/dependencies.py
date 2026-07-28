from app.identity.api.dependencies import require_role
from app.identity.domain.value_objects import Role

require_payments_admin = require_role(Role.FINANCE_ADMIN)
