/**
 * BladeX Commercial License Agreement
 * Copyright (c) 2018-2099, https://bladex.cn. All rights reserved.
 * <p>
 * Use of this software is governed by the Commercial License Agreement
 * obtained after purchasing a license from BladeX.
 * <p>
 * 1. This software is for development use only under a valid license
 * from BladeX.
 * <p>
 * 2. Redistribution of this software's source code to any third party
 * without a commercial license is strictly prohibited.
 * <p>
 * 3. Licensees may copyright their own code but cannot use segments
 * from this software for such purposes. Copyright of this software
 * remains with BladeX.
 * <p>
 * Using this software signifies agreement to this License, and the software
 * must not be used for illegal purposes.
 * <p>
 * THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY. The author is
 * not liable for any claims arising from secondary or illegal development.
 * <p>
 * Author: Chill Zhuang (bladejava@qq.com)
 */
package org.springblade.flow.business.service.impl;

import lombok.AllArgsConstructor;
import org.flowable.engine.IdentityService;
import org.flowable.engine.RuntimeService;
import org.flowable.engine.TaskService;
import org.flowable.engine.runtime.ProcessInstance;
import org.springblade.core.tool.api.R;
import org.springblade.core.tool.support.Kv;
import org.springblade.core.tool.utils.Func;
import org.springblade.core.tool.utils.StringUtil;
import org.springblade.flow.business.service.IFlowService;
import org.springblade.flow.core.entity.BladeFlow;
import org.springblade.flow.core.utils.TaskUtil;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 流程实现类
 *
 * @author Chill
 */
@RestController
@AllArgsConstructor
public class FlowServiceImpl implements IFlowService {

	private final RuntimeService runtimeService;
	private final IdentityService identityService;
	private final TaskService taskService;

	@Override
	public BladeFlow startProcessInstanceById(String processDefinitionId, String businessKey, Map<String, Object> variables) {
		// 设置流程启动用户
		identityService.setAuthenticatedUserId(TaskUtil.getTaskUser());
		// 开启流程
		ProcessInstance processInstance = runtimeService.startProcessInstanceById(processDefinitionId, businessKey, variables);
		// 组装流程通用类
		BladeFlow flow = new BladeFlow();
		flow.setProcessInstanceId(processInstance.getId());
		return flow;
	}

	@Override
	public BladeFlow startProcessInstanceByKey(String processDefinitionKey, String businessKey, Map<String, Object> variables) {
		// 设置流程启动用户
		identityService.setAuthenticatedUserId(TaskUtil.getTaskUser());
		// 开启流程
		ProcessInstance processInstance = runtimeService.startProcessInstanceByKey(processDefinitionKey, businessKey, variables);
		// 组装流程通用类
		BladeFlow flow = new BladeFlow();
		flow.setProcessInstanceId(processInstance.getId());
		return flow;
	}

	@Override
	public boolean completeTask(String taskId, String processInstanceId, String comment, Map<String, Object> variables) {
		// 增加评论
		if (StringUtil.isNoneBlank(processInstanceId, comment)) {
			taskService.addComment(taskId, processInstanceId, comment);
		}
		// 非空判断
		if (Func.isEmpty(variables)) {
			variables = Kv.create();
		}
		// 完成任务
		taskService.complete(taskId, variables);
		return true;
	}

	@Override
	public Object taskVariable(String taskId, String variableName) {
		return R.data(taskService.getVariable(taskId, variableName));
	}

	@Override
	public Map<String, Object> taskVariables(String taskId) {
		return taskService.getVariables(taskId);
	}

}
