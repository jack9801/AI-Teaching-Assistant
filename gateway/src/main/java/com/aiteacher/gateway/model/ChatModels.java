package com.aiteacher.gateway.model;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
public final class ChatModels {
 private ChatModels(){}
 public record ChatRequest(@NotBlank @Size(max=128) String sessionId,@NotBlank @Size(max=8000) String message){}
 public record ChatMessage(String role,String content){}
 public record WorkerSseEvent(String type,String delta,String requestId,String message){}
}
