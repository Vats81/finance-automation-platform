from app.identity.api.dependencies import require_role
from app.identity.domain.value_objects import Role

# Vendor onboarding (create/update) is an AP function; activation is
# compliance-sensitive (it's the point a vendor becomes payable) and
# reserved for Finance Admins.
require_vendor_writer = require_role(Role.AP_CLERK, Role.FINANCE_ADMIN)
require_vendor_activator = require_role(Role.FINANCE_ADMIN)
