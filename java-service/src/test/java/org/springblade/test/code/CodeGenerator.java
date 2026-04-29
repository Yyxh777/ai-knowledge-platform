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
package org.springblade.test.code;


import org.springblade.develop.constant.DevelopConstant;
import org.springblade.develop.support.BladeFastCodeGenerator;

/**
 * 代码生成器
 *
 * @author Chill
 */
public class CodeGenerator {

	/**
	 * 代码生成的系统类型(Boot/Cloud)
	 */
	public static String SYSTEM_NAME = DevelopConstant.BOOT_NAME;
	/**
	 * 代码生成的模块名
	 */
	public static String CODE_NAME = "系统模块";
	/**
	 * 代码所在服务名
	 */
	public static String SERVICE_NAME = "blade-system";
	/**
	 * 代码生成的包名
	 */
	public static String PACKAGE_NAME = "org.springblade.modules.system";
	/**
	 * 需要去掉的表前缀
	 */
	public static String[] TABLE_PREFIX = {"aikp_"};
	/**
	 * 需要生成的表名(两者只能取其一)
	 */
	public static String[] INCLUDE_TABLES = {"aikp_role_level"};
	/**
	 * 需要排除的表名(两者只能取其一)
	 */
	public static String[] EXCLUDE_TABLES = {};
	/**
	 * 是否包含基础业务字段
	 */
	public static Boolean HAS_SUPER_ENTITY = Boolean.TRUE;
	/**
	 * 基础业务字段
	 */
	public static String[] SUPER_ENTITY_COLUMNS = {"id", "create_time", "create_user", "create_dept", "update_time", "update_user", "status", "is_deleted"};

	/**
	 * RUN THIS
	 */
	public static void main(String[] args) {
		BladeFastCodeGenerator generator = new BladeFastCodeGenerator();
		generator.setSystemName(SYSTEM_NAME);
		generator.setCodeName(CODE_NAME);
		generator.setServiceName(SERVICE_NAME);
		generator.setPackageName(PACKAGE_NAME);
		generator.setTablePrefix(TABLE_PREFIX);
		generator.setIncludeTables(INCLUDE_TABLES);
		generator.setExcludeTables(EXCLUDE_TABLES);
		generator.setHasSuperEntity(HAS_SUPER_ENTITY);
		generator.setSuperEntityColumns(SUPER_ENTITY_COLUMNS);
		generator.run();
	}

}
