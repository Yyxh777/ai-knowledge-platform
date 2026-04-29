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
package org.springblade.modules.system.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import org.springblade.modules.system.pojo.entity.Role;
import org.springblade.modules.system.pojo.vo.RoleVO;

import jakarta.validation.constraints.NotEmpty;

import java.util.List;

/**
 * 服务类
 *
 * @author Chill
 */
public interface IRoleService extends IService<Role> {

	/**
	 * 自定义分页
	 *
	 * @param page 分页
	 * @param role 角色
	 * @return 分页
	 */
	IPage<RoleVO> selectRolePage(IPage<RoleVO> page, RoleVO role);

	/**
	 * 树形结构
	 *
	 * @param tenantId 租户id
	 * @return 角色列表
	 */
	List<RoleVO> tree(String tenantId);

	/**
	 * 权限配置
	 *
	 * @param roleIds      角色id集合
	 * @param menuIds      菜单id集合
	 * @param dataScopeIds 数据权限id集合
	 * @param apiScopeIds  接口权限id集合
	 * @return 是否成功
	 */
	boolean grant(@NotEmpty List<Long> roleIds, List<Long> menuIds, List<Long> dataScopeIds, List<Long> apiScopeIds);

	/**
	 * 获取角色ID
	 *
	 * @param tenantId  租户id
	 * @param roleNames 角色名
	 * @return 角色id
	 */
	String getRoleIds(String tenantId, String roleNames);

	/**
	 * 获取角色名
	 *
	 * @param roleIds 角色id
	 * @return 角色名
	 */
	List<String> getRoleNames(String roleIds);

	/**
	 * 获取角色名
	 *
	 * @param roleIds 角色id
	 * @return 角色别名
	 */
	List<String> getRoleAliases(String roleIds);

	/**
	 * 提交
	 *
	 * @param role 角色
	 * @return boolean
	 */
	boolean submit(Role role);

	/**
	 * 角色信息查询
	 *
	 * @param roleName 角色名
	 * @param parentId 父级id
	 * @return 角色列表
	 */
	List<RoleVO> search(String roleName, Long parentId);

	/**
	 * 删除角色
	 *
	 * @param ids 主键集合
	 * @return boolean
	 */
	boolean removeRole(String ids);

	/**
	 * 获取角色别名列表
	 *
	 * @param tenantId 租户id
	 * @return 别名列表
	 */
	List<Role> alias(String tenantId);


}
