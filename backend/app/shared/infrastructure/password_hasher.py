import bcrypt

from app.shared.application.ports import IPasswordHasher


class BcryptPasswordHasher(IPasswordHasher):
    def hash(self, plaintext: str) -> str:
        return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify(self, plaintext: str, hashed: str) -> bool:
        return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))
