package com.aiteacher.gateway;
import com.aiteacher.gateway.model.ChatModels.ChatMessage;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import java.time.Duration;
@Service
public class SessionService {
 private final ReactiveStringRedisTemplate redis; private final ObjectMapper mapper;
 public SessionService(ReactiveStringRedisTemplate redis,ObjectMapper mapper){this.redis=redis;this.mapper=mapper;}
 private String key(String id){return "chat:session:"+id;}
 public Flux<ChatMessage> history(String id){return redis.opsForList().range(key(id),0,-1).flatMap(this::decode);}
 public Mono<Long> append(String id,ChatMessage m){return encode(m).flatMap(v->redis.opsForList().rightPush(key(id),v)).flatMap(n->redis.expire(key(id),Duration.ofHours(24)).thenReturn(n));}
 public Mono<Void> appendPair(String id,ChatMessage u,ChatMessage a){return append(id,u).then(append(id,a)).then();}
 private Mono<ChatMessage> decode(String s){try{return Mono.just(mapper.readValue(s,ChatMessage.class));}catch(JsonProcessingException e){return Mono.error(new IllegalStateException("Corrupt session history",e));}}
 private Mono<String> encode(ChatMessage m){try{return Mono.just(mapper.writeValueAsString(m));}catch(JsonProcessingException e){return Mono.error(new IllegalStateException("Unable to serialize message",e));}}
}
