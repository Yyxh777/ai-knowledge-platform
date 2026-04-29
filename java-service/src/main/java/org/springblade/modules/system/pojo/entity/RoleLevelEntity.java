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
package org.springblade.modules.system.pojo.entity;

import lombok.Data;
import io.swagger.v3.oas.annotations.media.Schema;
import com.baomidou.mybatisplus.annotation.TableName;
import org.springblade.core.tenant.mp.TenantEntity;
import lombok.EqualsAndHashCode;
import java.io.Serial;

/**
 *  实体类
 *
 * @author kj
 * @since 2026-02-28
 */
@Data
@TableName("aikp_role_level")
@Schema(description = "RoleLevelEntity对象")
@EqualsAndHashCode(callSuper = true)
public class RoleLevelEntity extends TenantEntity {

	@Serial
	private static final long serialVersionUID = 1L;

	/**
	 * 角色id
	 */
	@Schema(description = "角色id")
	private Long roleId;
	/**
	 * 权限等级编码
	 */
	@Schema(description = "权限等级编码")
	private String levelCode;
	/**
	 * 备注
	 */
	@Schema(description = "备注")
	private String remark;

}
