package com.aiteacher.gateway;

import com.aiteacher.gateway.model.ChatModels.ChatMessage;
import com.aiteacher.gateway.model.ChatModels.WorkerSseEvent;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.List;

@Service
public class AiWorkerClient {
    private static final ParameterizedTypeReference<ServerSentEvent<String>> SSE_TYPE =
            new ParameterizedTypeReference<>() {};

    private final WebClient worker;
    private final ObjectMapper mapper;
    private final String sharedSecret;

    public AiWorkerClient(
            WebClient worker,
            ObjectMapper mapper,
            @Value("${app.worker.shared-secret}") String sharedSecret) {
        this.worker = worker;
        this.mapper = mapper;
        this.sharedSecret = sharedSecret;
    }

    public Flux<WorkerSseEvent> evaluate(String sessionId, List<ChatMessage> history) {
        return worker.post()
                .uri("/internal/evaluate")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .headers(headers -> {
                    if (!sharedSecret.isBlank()) {
                        headers.set("X-Worker-Token", sharedSecret);
                    }
                })
                .bodyValue(new WorkerRequest(sessionId, history))
                .retrieve()
                .bodyToFlux(SSE_TYPE)
                .map(ServerSentEvent::data)
                .filter(data -> data != null && !data.isBlank())
                .flatMap(this::parse)
                .timeout(Duration.ofSeconds(25))
                .onErrorResume(this::workerFailure);
    }

    private Mono<WorkerSseEvent> parse(String json) {
        try {
            return Mono.just(mapper.readValue(json, WorkerSseEvent.class));
        } catch (JsonProcessingException e) {
            return Mono.just(new WorkerSseEvent(
                    "error", null, null, "Malformed worker event"));
        }
    }

    private Flux<WorkerSseEvent> workerFailure(Throwable ex) {
        String message = ex instanceof java.util.concurrent.TimeoutException
                ? "The tutor worker timed out. Please try again."
                : "The tutor service is temporarily unavailable. Please try again.";
        return Flux.just(new WorkerSseEvent("error", null, null, message));
    }

    private record WorkerRequest(String sessionId, List<ChatMessage> messages) {}
}
