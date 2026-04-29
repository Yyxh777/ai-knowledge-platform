package org.springblade.modules.ai.client;

import org.springblade.modules.ai.dto.ChatResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Component
public class AiClient {

	public String chat(String question) {
		RestTemplate restTemplate = new RestTemplate();
		Map<String, String> body = new HashMap<>();
		body.put("query", question);

		ResponseEntity<ChatResponse> response =
			restTemplate.postForEntity(
				"http://localhost:8000/ai/chat",
				body,
				ChatResponse.class
			);

		return response.getBody().getAnswer();
	}


}
