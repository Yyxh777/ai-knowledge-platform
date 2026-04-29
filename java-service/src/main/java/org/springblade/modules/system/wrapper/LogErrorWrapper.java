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
package org.springblade.modules.system.wrapper;

import org.springblade.core.log.model.LogError;
import org.springblade.core.mp.support.BaseEntityWrapper;
import org.springblade.core.tool.utils.BeanUtil;
import org.springblade.modules.system.pojo.vo.LogErrorVO;

import java.util.Objects;

/**
 * Log包装类,返回视图层所需的字段
 *
 * @author Chill
 */
public class LogErrorWrapper extends BaseEntityWrapper<LogError, LogErrorVO> {

	public static LogErrorWrapper build() {
		return new LogErrorWrapper();
	}

	@Override
	public LogErrorVO entityVO(LogError logError) {
		return Objects.requireNonNull(BeanUtil.copyProperties(logError, LogErrorVO.class));
	}
}
