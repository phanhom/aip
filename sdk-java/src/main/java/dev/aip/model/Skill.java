package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * Structured skill descriptor for rich agent discovery.
 */
@JsonInclude(NON_NULL)
public record Skill(
        @JsonProperty("id") String id,
        @JsonProperty("name") String name,
        @JsonProperty("description") String description,
        @JsonProperty("tags") List<String> tags,
        @JsonProperty("input_modes") List<String> inputModes,
        @JsonProperty("output_modes") List<String> outputModes,
        @JsonProperty("input_schema") Map<String, Object> inputSchema,
        @JsonProperty("output_schema") Map<String, Object> outputSchema,
        @JsonProperty("examples") List<Map<String, Object>> examples
) {
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String id;
        private String name;
        private String description;
        private List<String> tags;
        private List<String> inputModes;
        private List<String> outputModes;
        private Map<String, Object> inputSchema;
        private Map<String, Object> outputSchema;
        private List<Map<String, Object>> examples;

        public Builder id(String id) {
            this.id = id;
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

        public Builder tags(List<String> tags) {
            this.tags = tags;
            return this;
        }

        public Builder inputModes(List<String> inputModes) {
            this.inputModes = inputModes;
            return this;
        }

        public Builder outputModes(List<String> outputModes) {
            this.outputModes = outputModes;
            return this;
        }

        public Builder inputSchema(Map<String, Object> inputSchema) {
            this.inputSchema = inputSchema;
            return this;
        }

        public Builder outputSchema(Map<String, Object> outputSchema) {
            this.outputSchema = outputSchema;
            return this;
        }

        public Builder examples(List<Map<String, Object>> examples) {
            this.examples = examples;
            return this;
        }

        public Skill build() {
            return new Skill(id, name, description, tags, inputModes, outputModes,
                    inputSchema, outputSchema, examples);
        }
    }
}
