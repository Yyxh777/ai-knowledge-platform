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
package org.springblade.common.cache;

import org.springblade.core.cache.utils.CacheUtil;
import org.springblade.core.tool.utils.SpringUtil;
import org.springblade.modules.system.pojo.entity.Param;
import org.springblade.modules.system.service.IParamService;

import static org.springblade.core.cache.constant.CacheConstant.PARAM_CACHE;

/**
 * 参数缓存工具类
 *
 * @author Chill
 */
public class ParamCache {

	private static final String PARAM_ID = "param:id:";
	private static final String PARAM_VALUE = "param:value:";

	private static final IParamService paramService;

	static {
		paramService = SpringUtil.getBean(IParamService.class);
	}

	/**
	 * 获取参数实体
	 *
	 * @param id 主键
	 * @return Param
	 */
	public static Param getById(Long id) {
		return CacheUtil.get(PARAM_CACHE, PARAM_ID, id, () -> paramService.getById(id));
	}

	/**
	 * 获取参数配置
	 *
	 * @param paramKey 参数值
	 * @return String
	 */
	public static String getValue(String paramKey) {
		return CacheUtil.get(PARAM_CACHE, PARAM_VALUE, paramKey, () -> paramService.getValue(paramKey));
	}

}
