package org.springblade.modules.ai.service.impl;

import lombok.AllArgsConstructor;
import org.springblade.modules.ai.client.AiClient;
import org.springblade.modules.ai.dto.ChatRequest;
import org.springblade.modules.ai.dto.ChatResponse;
import org.springblade.modules.ai.service.ChatService;
import org.springframework.stereotype.Service;

@Service
@AllArgsConstructor
public class ChatServiceImpl implements ChatService {


	private final AiClient aiClient;

	@Override
	public ChatResponse chat(ChatRequest request) {
		String answer = aiClient.chat(request.getQuestion());
		return new ChatResponse(answer);
	}
}
