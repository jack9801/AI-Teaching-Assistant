package com.aiteacher.gateway.config;
import io.netty.channel.ChannelOption;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;
import reactor.netty.resources.ConnectionProvider;
import java.time.Duration;
@Configuration
public class WebClientConfig {
 @Bean WebClient workerWebClient(@Value("${app.worker.base-url}") String url,@Value("${app.worker.connect-timeout-ms}") int timeout,@Value("${app.worker.response-timeout-seconds}") long response){
  var pool=ConnectionProvider.builder("worker-pool").maxConnections(1000).pendingAcquireTimeout(Duration.ofSeconds(2)).build();
  var client=HttpClient.create(pool).option(ChannelOption.CONNECT_TIMEOUT_MILLIS,timeout).responseTimeout(Duration.ofSeconds(response));
  return WebClient.builder().baseUrl(url).clientConnector(new ReactorClientHttpConnector(client)).build();
 }
}
