"""The firm permission policy, in one place (mirrors business/api/permissions.py).

| Capability                          | Owner | Admin | Accountant | Viewer |
|-------------------------------------|:-----:|:-----:|:----------:|:------:|
| See the firm, staff and clients     |  yes  |  yes  |    yes     |  yes   |
| Open a client business              | as the matching business role (see firms/application/access.py) |
| Add / release a client business     |  yes  |  yes  |     no     |   no   |
| Invite, re-role or remove staff     |  yes  |  yes* |     no     |   no   |

* Nobody can change, remove or grant the Owner role.
"""

from app.firms.domain.value_objects import FirmRole

ANY_STAFF: tuple[FirmRole, ...] = ()
MANAGE_FIRM = (FirmRole.OWNER, FirmRole.ADMIN)
