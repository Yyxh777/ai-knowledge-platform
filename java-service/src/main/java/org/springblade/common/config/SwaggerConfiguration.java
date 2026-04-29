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
import org.springblade.core.launch.constant.AppConstant;
import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Swagger配置类
 *
 * @author Chill
 */
@Configuration(proxyBeanMethods = false)
@AllArgsConstructor
@ConditionalOnProperty(value = "swagger.enabled", havingValue = "true", matchIfMissing = true)
public class SwaggerConfiguration {

	@Bean
	public GroupedOpenApi authApi() {
		return GroupedOpenApi.builder()
			.group("授权模块")
			.packagesToScan(AppConstant.BASE_PACKAGES + ".core.oauth2", AppConstant.BASE_PACKAGES + ".modules.auth")
			.build();
	}

	@Bean
	public GroupedOpenApi sysApi() {
		return GroupedOpenApi.builder()
			.group("系统模块")
			.packagesToScan(AppConstant.BASE_PACKAGES + ".modules.system", AppConstant.BASE_PACKAGES + ".modules.resource")
			.build();
	}

	@Bean
	public GroupedOpenApi flowApi() {
		// 创建并返回GroupedOpenApi对象
		return GroupedOpenApi.builder()
			.group("工作流模块")
			.packagesToScan(AppConstant.BASE_PACKAGES + ".flow")
			.build();
	}

}
