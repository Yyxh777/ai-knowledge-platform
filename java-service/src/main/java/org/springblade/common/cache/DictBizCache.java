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

import org.springblade.common.enums.DictBizEnum;
import org.springblade.core.cache.utils.CacheUtil;
import org.springblade.core.secure.utils.AuthUtil;
import org.springblade.core.tool.utils.SpringUtil;
import org.springblade.core.tool.utils.StringPool;
import org.springblade.modules.system.pojo.entity.DictBiz;
import org.springblade.modules.system.service.IDictBizService;

import java.util.List;

import static org.springblade.core.cache.constant.CacheConstant.DICT_CACHE;

/**
 * 业务字典缓存工具类
 *
 * @author Chill
 */
public class DictBizCache {

	private static final String DICT_ID = "dictBiz:id";
	private static final String DICT_VALUE = "dictBiz:value";
	private static final String DICT_LIST = "dictBiz:list";

	private static final IDictBizService dictService;

	static {
		dictService = SpringUtil.getBean(IDictBizService.class);
	}

	/**
	 * 获取字典实体
	 *
	 * @param id 主键
	 * @return DictBiz
	 */
	public static DictBiz getById(Long id) {
		String keyPrefix = DICT_ID.concat(StringPool.DASH).concat(AuthUtil.getTenantId()).concat(StringPool.COLON);
		return CacheUtil.get(DICT_CACHE, keyPrefix, id, () -> dictService.getById(id));
	}

	/**
	 * 获取字典值
	 *
	 * @param code    字典编号枚举
	 * @param dictKey Integer型字典键
	 * @return String
	 */
	public static String getValue(DictBizEnum code, Integer dictKey) {
		return getValue(code.getName(), dictKey);
	}

	/**
	 * 获取字典值
	 *
	 * @param code    字典编号
	 * @param dictKey Integer型字典键
	 * @return String
	 */
	public static String getValue(String code, Integer dictKey) {
		String keyPrefix = DICT_VALUE.concat(StringPool.DASH).concat(AuthUtil.getTenantId()).concat(StringPool.COLON);
		return CacheUtil.get(DICT_CACHE, keyPrefix + code + StringPool.COLON, String.valueOf(dictKey), () -> dictService.getValue(code, String.valueOf(dictKey)));
	}

	/**
	 * 获取字典值
	 *
	 * @param code    字典编号枚举
	 * @param dictKey String型字典键
	 * @return String
	 */
	public static String getValue(DictBizEnum code, String dictKey) {
		return getValue(code.getName(), dictKey);
	}

	/**
	 * 获取字典值
	 *
	 * @param code    字典编号
	 * @param dictKey String型字典键
	 * @return String
	 */
	public static String getValue(String code, String dictKey) {
		String keyPrefix = DICT_VALUE.concat(StringPool.DASH).concat(AuthUtil.getTenantId()).concat(StringPool.COLON);
		return CacheUtil.get(DICT_CACHE, keyPrefix + code + StringPool.COLON, dictKey, () -> dictService.getValue(code, dictKey));
	}

	/**
	 * 获取字典集合
	 *
	 * @param code 字典编号
	 * @return List<DictBiz>
	 */
	public static List<DictBiz> getList(String code) {
		String keyPrefix = DICT_LIST.concat(StringPool.DASH).concat(AuthUtil.getTenantId()).concat(StringPool.COLON);
		return CacheUtil.get(DICT_CACHE, keyPrefix, code, () -> dictService.getList(code));
	}

}
