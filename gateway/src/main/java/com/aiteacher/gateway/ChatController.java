package com.aiteacher.gateway;
import com.aiteacher.gateway.model.ChatModels.*;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import java.util.ArrayList;
@RestController
@RequestMapping("/api/v1")
public class ChatController {
 private final SessionService sessions; private final AiWorkerClient worker;
 public ChatController(SessionService sessions,AiWorkerClient worker){this.sessions=sessions;this.worker=worker;}
 @PostMapping(value="/chat",produces=MediaType.TEXT_EVENT_STREAM_VALUE)
 public Flux<ServerSentEvent<String>> chat(@Valid @RequestBody ChatRequest req){
  var user=new ChatMessage("user",req.message());
  return sessions.history(req.sessionId()).collectList().flatMapMany(history->{var outbound=new ArrayList<>(history);outbound.add(user);var text=new StringBuilder();
   return worker.evaluate(req.sessionId(),outbound).doOnNext(e->{if("text".equals(e.type())&&e.delta()!=null)text.append(e.delta());})
    .concatWith(Mono.defer(()->text.isEmpty()?Mono.empty():sessions.appendPair(req.sessionId(),user,new ChatMessage("assistant",text.toString().trim())).then(Mono.empty())))
    .map(e->ServerSentEvent.<String>builder().event(e.type()).data(e.delta()!=null?e.delta():e.message()!=null?e.message():"").build());});
 }
}
