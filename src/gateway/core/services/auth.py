from base64 import b64encode
from typing import Any, Protocol

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .client import HttpClientMixin


class AuthenticationStrategy(Protocol):
    async def authenticate(self, **kwargs: Any) -> dict[str, str] | None: ...


class UserLoginAuth(AuthenticationStrategy, HttpClientMixin):
    def __init__(self, *, url: str, login_key: str = "username"):
        self.base_url = url
        self.login_key = login_key

    async def authenticate(self, **kwargs: Any) -> dict[str, str] | None:
        username = str(kwargs.get("username", ""))
        password = str(kwargs.get("password", ""))

        if not username or not password:
            return None

        response = await self.post(
            self.base_url, json={self.login_key: username, "password": password}
        )
        response_json = await response.json()
        return dict[str, str](response_json) if response_json else None


class ServiceTokenExchangeAuth(AuthenticationStrategy, HttpClientMixin):
    def __init__(self, *, url: str, public_key: rsa.RSAPublicKey):
        self.base_url = url
        self.public_key = public_key

    def _encrypt_actor_id(self, actor_id: str) -> str:
        encrypted = self.public_key.encrypt(
            actor_id.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return b64encode(encrypted).decode()

    async def authenticate(self, **kwargs: Any) -> dict[str, str] | None:
        actor_id = str(kwargs.get("actor_id", ""))
        scopes = list(kwargs.get("scopes", []))
        if not actor_id:
            return None
        response = await self.post(
            self.base_url,
            headers={"X-Actor-ID": self._encrypt_actor_id(actor_id)},
            json={"scopes": scopes},
        )
        response_body = dict[str, str](response.json())
        return response_body if response_body else None


class AuthContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: str = Field()
    base_url: str | None = None
    public_key: rsa.RSAPublicKey | None = None
    strategy_name: str = Field(..., alias="strategy")
    extras: dict[str, Any] = Field(default_factory=dict)

    @field_validator("strategy_name")
    def validate_strategy_name(cls, v: str) -> str:
        if v not in {"user_login", "service_token_exchange"}:
            raise ValueError(f"Unsupported authentication strategy: {v}")
        return v

    @property
    def url(self) -> str:
        return f"{(self.base_url or '').strip('/')}/{self.path.strip('/')}"

    @property
    def strategy(self) -> AuthenticationStrategy:
        if self.strategy_name == "user_login":
            return UserLoginAuth(
                url=self.url,
                login_key=str(self.extras.get("login_key", "username")),
            )
        elif self.strategy_name == "service_token_exchange":
            if not self.public_key:
                raise ValueError(
                    "Missing public key for auth strategy Service Token Exchange"
                )
            return ServiceTokenExchangeAuth(
                url=self.url,
                public_key=self.public_key,
            )
        else:
            raise ValueError(
                f"Unsupported authentication strategy: {self.strategy_name}"
            )

    async def auth(self, **kwargs: Any) -> dict[str, str] | None:
        return await self.strategy.authenticate(**kwargs)
