package com.aiteacher.gateway;
import com.aiteacher.gateway.model.ChatModels.ChatMessage;
import com.aiteacher.gateway.model.ChatModels.WorkerSseEvent;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
@Service
public class AiWorkerClient {
 private final WebClient worker; private final ObjectMapper mapper;
 public AiWorkerClient(WebClient worker,ObjectMapper mapper){this.worker=worker;this.mapper=mapper;}
 public Flux<WorkerSseEvent> evaluate(String sessionId,List<ChatMessage> history){
  return worker.post().uri("/internal/evaluate").contentType(MediaType.APPLICATION_JSON).accept(MediaType.TEXT_EVENT_STREAM)
   .bodyValue(new WorkerRequest(sessionId,history)).retrieve().bodyToFlux(DataBuffer.class)
   .map(b->{String s=b.toString(StandardCharsets.UTF_8);b.release();return s;})
   .flatMapIterable(s->s.split("\\n\\n")).map(String::trim).filter(s->s.startsWith("data:"))
   .map(s->s.substring(5).trim()).flatMap(this::parse).timeout(Duration.ofSeconds(25))
   .onErrorReturn(new WorkerSseEvent("error",null,null,"The tutor service is temporarily unavailable. Please try again."));
 }
 private Flux<WorkerSseEvent> parse(String json){try{return Flux.just(mapper.readValue(json,WorkerSseEvent.class));}catch(JsonProcessingException e){return Flux.just(new WorkerSseEvent("error",null,null,"Malformed worker event"));}}
 private record WorkerRequest(String sessionId,List<ChatMessage> messages){}
}
