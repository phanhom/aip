package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * Human-facing display metadata for dashboards, agent cards, and marketplace UIs.
 */
@JsonInclude(NON_NULL)
public record Presentation(
        @JsonProperty("display_name") String displayName,
        @JsonProperty("tagline") String tagline,
        @JsonProperty("description") String description,
        @JsonProperty("icon_url") String iconUrl,
        @JsonProperty("color") String color,
        @JsonProperty("locale") String locale,
        @JsonProperty("categories") List<String> categories,
        @JsonProperty("homepage_url") String homepageUrl,
        @JsonProperty("privacy_policy_url") String privacyPolicyUrl,
        @JsonProperty("tos_url") String tosUrl,
        @JsonProperty("provider") Provider provider
) {
    /** Minimal constructor with only the required field. */
    public Presentation(String displayName) {
        this(displayName, null, null, null, null, "en", null, null, null, null, null);
    }

    /**
     * Organization or individual that operates an agent.
     */
    @JsonInclude(NON_NULL)
    public record Provider(
            @JsonProperty("name") String name,
            @JsonProperty("url") String url
    ) {
        public Provider(String name) {
            this(name, null);
        }
    }
}
