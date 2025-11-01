# безопасный Redis-lock для бронирования слотов.




# Импорт модуля uuid. Нужен для генерации уникального токена для каждого лок-захвата.
import uuid
# единый доступ к Redis.
from .redis_client import redis_client


# Функция ставит лок атомарно и возвращает уникальный токен владельца. TTL защищает от вечных локов.
def acquire_lock(key: str, ttl:int):
    # Создаётся уникальный токен в виде строки
    token = str(uuid.uuid4())
    # Пытаемся установить ключ в Redis
    acquired = redis_client.set(key, token, nx=True,ex= ttl)
    # Если лок получен (acquired = True) возвращаем token. Иначе возвращаем None. Клиент использует token как подтверждение владения локом.
    return token if acquired else None

# Функция удаляет лок только если токен совпадает. Удаление выполняется атомарно через Lua, чтобы избежать гонок.
def release_lock(key: str, token: str):
    # Lua-скрипт для атомарного сравнения и удаления:
    lua = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
      return redis.call("del", KEYS[1])
    else
      return 0
    end
    """
    return redis_client.eval(lua, 1, key, token)