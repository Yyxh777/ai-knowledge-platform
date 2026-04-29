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

package org.springblade.common.config;

import lombok.AllArgsConstructor;
import org.springblade.common.event.ApiLogListener;
import org.springblade.common.event.ErrorLogListener;
import org.springblade.common.event.UsualLogListener;
import org.springblade.core.launch.props.BladeProperties;
import org.springblade.core.launch.server.ServerInfo;
import org.springblade.modules.system.service.ILogService;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 日志工具自动配置
 *
 * @author Chill
 */
@Configuration(proxyBeanMethods = false)
@AllArgsConstructor
public class BladeLogConfiguration {

	private final ILogService logService;
	private final ServerInfo serverInfo;
	private final BladeProperties bladeProperties;

	@Bean(name = "apiLogListener")
	public ApiLogListener apiLogListener() {
		return new ApiLogListener(logService, serverInfo, bladeProperties);
	}

	@Bean(name = "errorEventListener")
	public ErrorLogListener errorEventListener() {
		return new ErrorLogListener(logService, serverInfo, bladeProperties);
	}

	@Bean(name = "usualEventListener")
	public UsualLogListener usualEventListener() {
		return new UsualLogListener(logService, serverInfo, bladeProperties);
	}

}
