package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * A file, document, or structured data produced during task execution.
 */
@JsonInclude(NON_NULL)
public record Artifact(
        @JsonProperty("artifact_id") String artifactId,
        @JsonProperty("name") String name,
        @JsonProperty("description") String description,
        @JsonProperty("mime_type") String mimeType,
        @JsonProperty("uri") String uri,
        @JsonProperty("inline_data") String inlineData,
        @JsonProperty("metadata") Map<String, Object> metadata
) {
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String artifactId;
        private String name;
        private String description;
        private String mimeType;
        private String uri;
        private String inlineData;
        private Map<String, Object> metadata;

        public Builder artifactId(String artifactId) {
            this.artifactId = artifactId;
            return this;
        }

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder description(String description) {
            this.description = description;
            return this;
        }

        public Builder mimeType(String mimeType) {
            this.mimeType = mimeType;
            return this;
        }

        public Builder uri(String uri) {
            this.uri = uri;
            return this;
        }

        public Builder inlineData(String inlineData) {
            this.inlineData = inlineData;
            return this;
        }

        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public Artifact build() {
            return new Artifact(artifactId, name, description, mimeType, uri, inlineData, metadata);
        }
    }
}
