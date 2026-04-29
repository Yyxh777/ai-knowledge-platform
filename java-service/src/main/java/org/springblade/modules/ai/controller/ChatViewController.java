package org.springblade.modules.ai.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping("/ai")
public class ChatViewController {

    /**
     * 提供 AI 聊天页面
     * 访问路径: http://localhost:端口/ai/chat-page
     */
    @GetMapping("/chat-page")
    public String chatPage() {
        return "redirect:/chat.html";
    }

    /**
     * 提供根路径访问
     * 访问路径: http://localhost:端口/ai/
     */
    @GetMapping("")
    public String index() {
        return "redirect:/chat.html";
    }
}
