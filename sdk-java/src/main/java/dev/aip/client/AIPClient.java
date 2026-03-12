package dev.aip.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import dev.aip.model.AIPAck;
import dev.aip.model.AIPMessage;
import dev.aip.model.AgentStatus;
import dev.aip.model.AIPTask;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Spliterator;
import java.util.Spliterators;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

/**
 * AIP protocol client for agent-to-agent communication.
 */
public class AIPClient {

    private static final String DEFAULT_API_VERSION = "v1";

    private final String baseUrl;
    private final String apiVersion;
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    /**
     * Creates a client with the given base URL and default API version (v1).
     *
     * @param baseUrl Base URL of the agent (e.g., "https://agent.example.com")
     */
    public AIPClient(String baseUrl) {
        this(baseUrl, DEFAULT_API_VERSION);
    }

    /**
     * Creates a client with the given base URL and API version.
     *
     * @param baseUrl     Base URL of the agent (e.g., "https://agent.example.com")
     * @param apiVersion API version (e.g., "v1")
     */
    public AIPClient(String baseUrl, String apiVersion) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.apiVersion = apiVersion;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
        this.objectMapper = new ObjectMapper()
                .registerModule(new JavaTimeModule())
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
    }

    /**
     * Sends a message (non-streaming, JSON).
     *
     * @param msg The message to send
     * @return The acknowledgment from the server
     */
    public AIPAck send(AIPMessage msg) throws Exception {
        return send(msg, null);
    }

    /**
     * Sends a message with an optional idempotency key.
     *
     * @param msg            The message to send
     * @param idempotencyKey Optional idempotency key (UUID v4) for deduplication
     * @return The acknowledgment from the server
     */
    public AIPAck send(AIPMessage msg, String idempotencyKey) throws Exception {
        String json = objectMapper.writeValueAsString(msg);
        String url = baseUrl + "/" + apiVersion + "/aip";

        var builder = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Accept", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .timeout(Duration.ofSeconds(30));
        if (idempotencyKey != null && !idempotencyKey.isBlank()) {
            builder.header("Idempotency-Key", idempotencyKey);
        }
        HttpRequest request = builder.build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));

        if (response.statusCode() >= 400) {
            throw new AIPClientException("HTTP " + response.statusCode() + ": " + response.body());
        }

        return objectMapper.readValue(response.body(), AIPAck.class);
    }

    /**
     * Sends a message with SSE streaming response.
     *
     * @param msg The message to send
     * @return Stream of SSE events (blocks as consumed)
     */
    public Stream<SSEEvent> sendStream(AIPMessage msg) throws Exception {
        String json = objectMapper.writeValueAsString(msg);
        String url = baseUrl + "/" + apiVersion + "/aip";

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Accept", "text/event-stream")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .timeout(Duration.ofMinutes(30))
                .build();

        HttpResponse<java.io.InputStream> response = httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());

        if (response.statusCode() >= 400) {
            try (var is = response.body()) {
                String body = new String(is.readAllBytes(), StandardCharsets.UTF_8);
                throw new AIPClientException("HTTP " + response.statusCode() + ": " + body);
            }
        }

        var reader = new BufferedReader(new InputStreamReader(response.body(), StandardCharsets.UTF_8));
        var iterator = new SSEIterator(reader);
        Spliterator<SSEEvent> spliterator = Spliterators.spliteratorUnknownSize(iterator, Spliterator.ORDERED | Spliterator.NONNULL);

        return StreamSupport.stream(spliterator, false).onClose(() -> {
            try {
                reader.close();
            } catch (Exception ignored) {
            }
        });
    }

    /**
     * Gets agent status (discovery).
     *
     * @return Agent status
     */
    public AgentStatus getStatus() throws Exception {
        String url = baseUrl + "/" + apiVersion + "/status";

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Accept", "application/json")
                .GET()
                .timeout(Duration.ofSeconds(10))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));

        if (response.statusCode() >= 400) {
            throw new AIPClientException("HTTP " + response.statusCode() + ": " + response.body());
        }

        return objectMapper.readValue(response.body(), AgentStatus.class);
    }

    /**
     * Gets a task by ID.
     *
     * @param taskId Task identifier
     * @return The task
     */
    public AIPTask getTask(String taskId) throws Exception {
        String url = baseUrl + "/" + apiVersion + "/tasks/" + taskId;

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Accept", "application/json")
                .GET()
                .timeout(Duration.ofSeconds(10))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));

        if (response.statusCode() >= 400) {
            throw new AIPClientException("HTTP " + response.statusCode() + ": " + response.body());
        }

        return objectMapper.readValue(response.body(), AIPTask.class);
    }

    /**
     * Cancels a task.
     *
     * @param taskId Task identifier
     * @return The updated task
     */
    public AIPTask cancelTask(String taskId) throws Exception {
        String url = baseUrl + "/" + apiVersion + "/tasks/" + taskId + "/cancel";

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.noBody())
                .timeout(Duration.ofSeconds(10))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));

        if (response.statusCode() >= 400) {
            throw new AIPClientException("HTTP " + response.statusCode() + ": " + response.body());
        }

        return objectMapper.readValue(response.body(), AIPTask.class);
    }

    private static class SSEIterator implements java.util.Iterator<SSEEvent> {
        private final BufferedReader reader;
        private SSEEvent next;
        private boolean exhausted;

        SSEIterator(BufferedReader reader) {
            this.reader = reader;
        }

        @Override
        public boolean hasNext() {
            if (exhausted) return false;
            if (next != null) return true;
            try {
                String eventType = "message";
                StringBuilder data = new StringBuilder();

                String line;
                while ((line = reader.readLine()) != null) {
                    if (line.startsWith("event:")) {
                        eventType = line.substring(6).trim();
                    } else if (line.startsWith("data:")) {
                        if (data.length() > 0) data.append("\n");
                        data.append(line.substring(5));
                    } else if (line.isEmpty()) {
                        if (data.length() > 0 || !eventType.equals("message")) {
                            next = new SSEEvent(eventType, data.toString());
                            return true;
                        }
                    }
                }
                exhausted = true;
                if (data.length() > 0) {
                    next = new SSEEvent(eventType, data.toString());
                    return true;
                }
            } catch (Exception e) {
                exhausted = true;
                throw new RuntimeException("SSE read error", e);
            }
            return false;
        }

        @Override
        public SSEEvent next() {
            if (!hasNext()) throw new java.util.NoSuchElementException();
            SSEEvent result = next;
            next = null;
            return result;
        }
    }

    /**
     * Exception thrown when the AIP client encounters an error.
     */
    public static class AIPClientException extends RuntimeException {
        public AIPClientException(String message) {
            super(message);
        }

        public AIPClientException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
