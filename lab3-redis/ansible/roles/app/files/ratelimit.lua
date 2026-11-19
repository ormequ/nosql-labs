-- sliding-window limiter: prune, count and add in one atomic script, KEY = ratelimit:<tier>:<api_key>
local key    = KEYS[1]
local limit  = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local now = tonumber(redis.call('TIME')[1])

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)

if count < limit then
  redis.call('ZADD', key, now, now .. '-' .. math.random())
  redis.call('EXPIRE', key, window)
  return {1, 0, limit - count - 1}
end

-- Retry-After from the oldest request still inside the window
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
return {0, oldest[2] + window - now, 0}
