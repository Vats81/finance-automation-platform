"""The beta permission policy in one place.

Every protected route names one of these tuples instead of spelling out roles,
so the policy can be read (and tested) as a single matrix:

| Capability                        | Owner | Admin | Accountant | Viewer |
|-----------------------------------|:-----:|:-----:|:----------:|:------:|
| View business records             |  yes  |  yes  |    yes     |  yes   |
| Create / edit records             |  yes  |  yes  |    yes     |   no   |
| Record payments, void             |  yes  |  yes  |    yes     |   no   |
| Import CSV                        |  yes  |  yes  |    yes     |   no   |
| Export / send reports             |  yes  |  yes  |    yes     |   no   |
| Manage team and roles             |  yes  |  yes* |     no     |   no   |
| Edit business settings            |  yes  |  yes* |     no     |   no   |
| Change plan, transfer, delete     |  yes  |   no  |     no     |   no   |

* An Admin can never change, remove or grant the Owner role; see
  UpdateTeamMemberRoleUseCase / InviteTeamMemberUseCase.
"""

from app.business.domain.value_objects import BusinessRole

ANY_MEMBER: tuple[BusinessRole, ...] = ()
CAN_WRITE = (BusinessRole.OWNER, BusinessRole.ADMIN, BusinessRole.ACCOUNTANT)
CAN_EXPORT = CAN_WRITE
CAN_MANAGE_TEAM = (BusinessRole.OWNER, BusinessRole.ADMIN)
CAN_EDIT_SETTINGS = (BusinessRole.OWNER, BusinessRole.ADMIN)
OWNER_ONLY = (BusinessRole.OWNER,)
