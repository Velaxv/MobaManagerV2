import json
import logging
from typing import Any, Optional, Dict
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class MockRedis:
    """
    Simulador assíncrono do Redis em memória (Mock).
    Evita a necessidade do serviço Redis rodando em notebooks corporativos.
    """
    def __init__(self):
        self._store: Dict[str, str] = {}
        logger.info("[MockRedis] Banco de dados em memória inicializado (Zero Dependency Mode).")

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = str(value)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        # Ignora TTL para o simulador simples em memória
        self._store[key] = str(value)

    async def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    async def incrby(self, key: str, amount: int) -> int:
        current = self._store.get(key, "0")
        try:
            val = int(current) + amount
        except ValueError:
            val = amount
        self._store[key] = str(val)
        return val

    async def publish(self, channel: str, message: str) -> None:
        logger.debug(f"[MockRedis PubSub] Mensagem publicada no canal {channel}: {message}")

    async def aclose(self) -> None:
        self._store.clear()
        logger.info("[MockRedis] Banco em memória limpo e fechado.")


class RedisClient:
    def __init__(self):
        self._client: Optional[Any] = None
        self._is_mock = settings.redis_url == "mock" or "localhost" not in settings.redis_url
    
    async def connect(self):
        if self._is_mock:
            self._client = MockRedis()
            logger.info("[RedisClient] Conectado ao simulador Redis em memória.")
        else:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=50,
                )
                # Testa conexão rápida
                await self._client.ping()
                logger.info("[RedisClient] Conectado ao Redis real.")
            except Exception as e:
                logger.warning(
                    f"[RedisClient] Falha ao conectar ao Redis real ({e}). "
                    "Ativando simulador em memória automaticamente."
                )
                self._client = MockRedis()
                self._is_mock = True
    
    async def disconnect(self):
        if self._client:
            await self._client.aclose()
    
    @property
    def client(self) -> Any:
        if not self._client:
            raise RuntimeError("Redis não conectado. Chame connect() primeiro.")
        return self._client
    
    # --- Métodos auxiliares para gerenciamento de estado do calendário ---
    
    async def set_calendar_state(self, league_id: str, state_data: dict, ttl: int = 86400) -> None:
        key = f"calendar:league:{league_id}:state"
        await self.client.setex(key, ttl, json.dumps(state_data))
    
    async def get_calendar_state(self, league_id: str) -> Optional[dict]:
        key = f"calendar:league:{league_id}:state"
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def set_draft_state(self, match_id: str, draft_data: dict, ttl: int = 3600) -> None:
        key = f"draft:match:{match_id}"
        await self.client.setex(key, ttl, json.dumps(draft_data))
    
    async def get_draft_state(self, match_id: str) -> Optional[dict]:
        key = f"draft:match:{match_id}"
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def cache_match_result(self, match_id: str, result: dict, ttl: int = 604800) -> None:
        key = f"match:result:{match_id}"
        await self.client.setex(key, ttl, json.dumps(result))
    
    async def get_match_result(self, match_id: str) -> Optional[dict]:
        key = f"match:result:{match_id}"
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def set_playoff_state(self, league_id: str, bracket: dict, ttl: int = 86400 * 60) -> None:
        key = f"playoffs:league:{league_id}"
        await self.client.setex(key, ttl, json.dumps(bracket))

    async def get_playoff_state(self, league_id: str) -> Optional[dict]:
        key = f"playoffs:league:{league_id}"
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def delete_playoff_state(self, league_id: str) -> None:
        key = f"playoffs:league:{league_id}"
        await self.client.delete(key)
    
    async def increment_burnout_counter(self, player_id: str, field: str, amount: int = 5) -> int:
        key = f"burnout:player:{player_id}:{field}"
        return await self.client.incrby(key, amount)
    
    async def set_generic(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        if ttl:
            await self.client.setex(key, ttl, serialized)
        else:
            await self.client.set(key, serialized)
    
    async def get_generic(self, key: str) -> Optional[Any]:
        data = await self.client.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    
    async def delete(self, key: str) -> None:
        await self.client.delete(key)
    
    async def publish(self, channel: str, message: dict) -> None:
        await self.client.publish(channel, json.dumps(message))

# Instância singleton do cliente Redis
redis_client = RedisClient()
