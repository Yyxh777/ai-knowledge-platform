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
package org.springblade.modules.system.controller;

import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import com.github.xiaoymin.knife4j.annotations.ApiOperationSupport;
import lombok.AllArgsConstructor;
import jakarta.validation.Valid;

import org.springblade.core.secure.BladeUser;
import org.springblade.core.secure.annotation.PreAuth;
import org.springblade.core.mp.support.Condition;
import org.springblade.core.mp.support.Query;
import org.springblade.core.tool.api.R;
import org.springblade.core.tool.utils.Func;
import org.springframework.web.bind.annotation.*;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import org.springblade.modules.system.pojo.entity.RoleLevelEntity;
import org.springblade.modules.system.pojo.vo.RoleLevelVO;
import org.springblade.modules.system.excel.RoleLevelExcel;
import org.springblade.modules.system.wrapper.RoleLevelWrapper;
import org.springblade.modules.system.service.IRoleLevelService;
import org.springblade.core.boot.ctrl.BladeController;
import org.springblade.core.tool.utils.DateUtil;
import org.springblade.core.excel.util.ExcelUtil;
import org.springblade.core.tool.constant.BladeConstant;
import org.springblade.core.tool.constant.RoleConstant;
import java.util.Map;
import java.util.List;
import jakarta.servlet.http.HttpServletResponse;

/**
 *  控制器
 *
 * @author kj
 * @since 2026-02-28
 */
@RestController
@AllArgsConstructor
@RequestMapping("/roleLevel")
@Tag(name = "", description = "接口")
public class RoleLevelController extends BladeController {

	private final IRoleLevelService roleLevelService;

	/**
	 *  详情
	 */
	@GetMapping("/detail")
	@ApiOperationSupport(order = 1)
	@Operation(summary = "详情", description  = "传入roleLevel")
	public R<RoleLevelVO> detail(RoleLevelEntity roleLevel) {
		RoleLevelEntity detail = roleLevelService.getOne(Condition.getQueryWrapper(roleLevel));
		return R.data(RoleLevelWrapper.build().entityVO(detail));
	}

	/**
	 *  分页
	 */
	@GetMapping("/list")
	@ApiOperationSupport(order = 2)
	@Operation(summary = "分页", description  = "传入roleLevel")
	public R<IPage<RoleLevelVO>> list(@Parameter(hidden = true) @RequestParam Map<String, Object> roleLevel, Query query) {
		IPage<RoleLevelEntity> pages = roleLevelService.page(Condition.getPage(query), Condition.getQueryWrapper(roleLevel, RoleLevelEntity.class));
		return R.data(RoleLevelWrapper.build().pageVO(pages));
	}


	/**
	 *  自定义分页
	 */
	@GetMapping("/page")
	@ApiOperationSupport(order = 3)
	@Operation(summary = "分页", description  = "传入roleLevel")
	public R<IPage<RoleLevelVO>> page(RoleLevelVO roleLevel, Query query) {
		IPage<RoleLevelVO> pages = roleLevelService.selectRoleLevelPage(Condition.getPage(query), roleLevel);
		return R.data(pages);
	}

	/**
	 *  新增
	 */
	@PostMapping("/save")
	@ApiOperationSupport(order = 4)
	@Operation(summary = "新增", description  = "传入roleLevel")
	public R save(@Valid @RequestBody RoleLevelEntity roleLevel) {
		return R.status(roleLevelService.save(roleLevel));
	}

	/**
	 *  修改
	 */
	@PostMapping("/update")
	@ApiOperationSupport(order = 5)
	@Operation(summary = "修改", description  = "传入roleLevel")
	public R update(@Valid @RequestBody RoleLevelEntity roleLevel) {
		return R.status(roleLevelService.updateById(roleLevel));
	}

	/**
	 *  新增或修改
	 */
	@PostMapping("/submit")
	@ApiOperationSupport(order = 6)
	@Operation(summary = "新增或修改", description  = "传入roleLevel")
	public R submit(@Valid @RequestBody RoleLevelEntity roleLevel) {
		return R.status(roleLevelService.saveOrUpdate(roleLevel));
	}

	/**
	 *  删除
	 */
	@PostMapping("/remove")
	@ApiOperationSupport(order = 7)
	@Operation(summary = "逻辑删除", description  = "传入ids")
	public R remove(@Parameter(description = "主键集合", required = true) @RequestParam String ids) {
		return R.status(roleLevelService.deleteLogic(Func.toLongList(ids)));
	}

	/**
	 * 导出数据
	 */
	@PreAuth(RoleConstant.HAS_ROLE_ADMIN)
	@GetMapping("/export-roleLevel")
	@ApiOperationSupport(order = 8)
	@Operation(summary = "导出数据", description  = "传入roleLevel")
	public void exportRoleLevel(@Parameter(hidden = true) @RequestParam Map<String, Object> roleLevel, BladeUser bladeUser, HttpServletResponse response) {
		QueryWrapper<RoleLevelEntity> queryWrapper = Condition.getQueryWrapper(roleLevel, RoleLevelEntity.class);
		//if (!AuthUtil.isAdministrator()) {
		//	queryWrapper.lambda().eq(RoleLevelEntity::getTenantId, bladeUser.getTenantId());
		//}
		//queryWrapper.lambda().eq(RoleLevelEntity::getIsDeleted, BladeConstant.DB_NOT_DELETED);
		List<RoleLevelExcel> list = roleLevelService.exportRoleLevel(queryWrapper);
		ExcelUtil.export(response, "数据" + DateUtil.time(), "数据表", list, RoleLevelExcel.class);
	}

}
