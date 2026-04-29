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
package org.springblade.flow.business.service;

import org.springblade.flow.core.entity.BladeFlow;

import java.util.Map;

/**
 * 工作流调用接口.
 *
 * @author Chill
 */
public interface IFlowService {

	/**
	 * 开启流程
	 *
	 * @param processDefinitionId 流程id
	 * @param businessKey         业务key
	 * @param variables           参数
	 * @return BladeFlow
	 */
	BladeFlow startProcessInstanceById(String processDefinitionId, String businessKey, Map<String, Object> variables);

	/**
	 * 开启流程
	 *
	 * @param processDefinitionKey 流程标识
	 * @param businessKey          业务key
	 * @param variables            参数
	 * @return BladeFlow
	 */
	BladeFlow startProcessInstanceByKey(String processDefinitionKey, String businessKey, Map<String, Object> variables);

	/**
	 * 完成任务
	 *
	 * @param taskId            任务id
	 * @param processInstanceId 流程实例id
	 * @param comment           评论
	 * @param variables         参数
	 * @return R
	 */
	boolean completeTask(String taskId, String processInstanceId, String comment, Map<String, Object> variables);

	/**
	 * 获取流程变量
	 *
	 * @param taskId       任务id
	 * @param variableName 变量名
	 * @return R
	 */
	Object taskVariable(String taskId, String variableName);

	/**
	 * 获取流程变量集合
	 *
	 * @param taskId 任务id
	 * @return R
	 */
	Map<String, Object> taskVariables(String taskId);
}
