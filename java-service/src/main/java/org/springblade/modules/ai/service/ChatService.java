package org.springblade.modules.ai.service;

import org.springblade.modules.ai.dto.ChatRequest;
import org.springblade.modules.ai.dto.ChatResponse;
import org.springframework.stereotype.Service;

public interface ChatService {

	/**
	 * 调用大模型
	 * @param request
	 * @return
	 */
	ChatResponse chat(ChatRequest request);

}
