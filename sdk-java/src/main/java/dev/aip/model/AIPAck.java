package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * Standard acknowledgment returned by POST /aip handlers.
 */
@JsonInclude(NON_NULL)
public record AIPAck(
        @JsonProperty("ok") boolean ok,
        @JsonProperty("message_id") String messageId,
        @JsonProperty("to") String to,
        @JsonProperty("status") String status,
        @JsonProperty("task_id") String taskId,
        @JsonProperty("error_code") String errorCode,
        @JsonProperty("error_message") String errorMessage,
        @JsonProperty("correlation_id") String correlationId
) {
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private boolean ok;
        private String messageId;
        private String to;
        private String status;
        private String taskId;
        private String errorCode;
        private String errorMessage;
        private String correlationId;

        public Builder ok(boolean ok) {
            this.ok = ok;
            return this;
        }

        public Builder messageId(String messageId) {
            this.messageId = messageId;
            return this;
        }

        public Builder to(String to) {
            this.to = to;
            return this;
        }

        public Builder status(String status) {
            this.status = status;
            return this;
        }

        public Builder taskId(String taskId) {
            this.taskId = taskId;
            return this;
        }

        public Builder errorCode(String errorCode) {
            this.errorCode = errorCode;
            return this;
        }

        public Builder errorMessage(String errorMessage) {
            this.errorMessage = errorMessage;
            return this;
        }

        public Builder correlationId(String correlationId) {
            this.correlationId = correlationId;
            return this;
        }

        public AIPAck build() {
            return new AIPAck(ok, messageId, to, status, taskId, errorCode, errorMessage, correlationId);
        }
    }
}
