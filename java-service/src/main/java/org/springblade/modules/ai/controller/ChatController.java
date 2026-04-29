package org.springblade.modules.ai.controller;

import lombok.AllArgsConstructor;
import org.springblade.modules.ai.dto.ChatRequest;
import org.springblade.modules.ai.dto.ChatResponse;
import org.springblade.modules.ai.service.ChatService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/chat")
@AllArgsConstructor
public class ChatController {

	private final ChatService chatService;


	@PostMapping
	public ChatResponse chat(ChatRequest request) {
		return chatService.chat(request);
	}


}
