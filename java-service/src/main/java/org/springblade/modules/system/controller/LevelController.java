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

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import com.github.xiaoymin.knife4j.annotations.ApiOperationSupport;
import lombok.AllArgsConstructor;
import jakarta.validation.Valid;

import org.apache.xmlbeans.impl.common.SystemCache;
import org.springblade.common.cache.UserCache;
import org.springblade.core.secure.BladeUser;
import org.springblade.core.secure.annotation.PreAuth;
import org.springblade.core.mp.support.Condition;
import org.springblade.core.mp.support.Query;
import org.springblade.core.secure.utils.AuthUtil;
import org.springblade.core.tool.api.R;
import org.springblade.core.tool.utils.Func;
import org.springblade.modules.system.pojo.entity.RoleLevelEntity;
import org.springblade.modules.system.pojo.entity.User;
import org.springblade.modules.system.service.IRoleLevelService;
import org.springframework.web.bind.annotation.*;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import org.springblade.modules.system.pojo.entity.LevelEntity;
import org.springblade.modules.system.pojo.vo.LevelVO;
import org.springblade.modules.system.excel.LevelExcel;
import org.springblade.modules.system.wrapper.LevelWrapper;
import org.springblade.modules.system.service.ILevelService;
import org.springblade.core.boot.ctrl.BladeController;
import org.springblade.core.tool.utils.DateUtil;
import org.springblade.core.excel.util.ExcelUtil;
import org.springblade.core.tool.constant.BladeConstant;
import org.springblade.core.tool.constant.RoleConstant;

import java.util.ArrayList;
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
@RequestMapping("/level")
@Tag(name = "", description = "接口")
public class LevelController extends BladeController {

	private final ILevelService levelService;

	private final IRoleLevelService roleLevelService;

	/**
	 *  获取登录用户的level数组
	 */
	@GetMapping("getByUser")
	@ApiOperationSupport(order = 1)
	@Operation(summary = "获取登录用户的level数组")
	public R<List<String>> getByUser() {
		User user = UserCache.getUser(AuthUtil.getUserId());
		if (Func.isEmpty(user)){
			return R.data(new ArrayList<>());
		}
		List<RoleLevelEntity> list = roleLevelService.list(new LambdaQueryWrapper<RoleLevelEntity>()
			.eq(RoleLevelEntity::getRoleId, user.getRoleId()));
		if (Func.isNotEmpty(list)){
			return R.data(list.stream().map(RoleLevelEntity::getLevelCode).toList());
		}
		return R.data(new ArrayList<>());
	}

	/**
	 *  详情
	 */
	@GetMapping("/detail")
	@ApiOperationSupport(order = 1)
	@Operation(summary = "详情", description  = "传入level")
	public R<LevelVO> detail(LevelEntity level) {
		LevelEntity detail = levelService.getOne(Condition.getQueryWrapper(level));
		return R.data(LevelWrapper.build().entityVO(detail));
	}

	/**
	 *  分页
	 */
	@GetMapping("/list")
	@ApiOperationSupport(order = 2)
	@Operation(summary = "分页", description  = "传入level")
	public R<IPage<LevelVO>> list(@Parameter(hidden = true) @RequestParam Map<String, Object> level, Query query) {
		IPage<LevelEntity> pages = levelService.page(Condition.getPage(query), Condition.getQueryWrapper(level, LevelEntity.class));
		return R.data(LevelWrapper.build().pageVO(pages));
	}


	/**
	 *  自定义分页
	 */
	@GetMapping("/page")
	@ApiOperationSupport(order = 3)
	@Operation(summary = "分页", description  = "传入level")
	public R<IPage<LevelVO>> page(LevelVO level, Query query) {
		IPage<LevelVO> pages = levelService.selectLevelPage(Condition.getPage(query), level);
		return R.data(pages);
	}

	/**
	 *  新增
	 */
	@PostMapping("/save")
	@ApiOperationSupport(order = 4)
	@Operation(summary = "新增", description  = "传入level")
	public R save(@Valid @RequestBody LevelEntity level) {
		return R.status(levelService.save(level));
	}

	/**
	 *  修改
	 */
	@PostMapping("/update")
	@ApiOperationSupport(order = 5)
	@Operation(summary = "修改", description  = "传入level")
	public R update(@Valid @RequestBody LevelEntity level) {
		return R.status(levelService.updateById(level));
	}

	/**
	 *  新增或修改
	 */
	@PostMapping("/submit")
	@ApiOperationSupport(order = 6)
	@Operation(summary = "新增或修改", description  = "传入level")
	public R submit(@Valid @RequestBody LevelEntity level) {
		return R.status(levelService.saveOrUpdate(level));
	}

	/**
	 *  删除
	 */
	@PostMapping("/remove")
	@ApiOperationSupport(order = 7)
	@Operation(summary = "逻辑删除", description  = "传入ids")
	public R remove(@Parameter(description = "主键集合", required = true) @RequestParam String ids) {
		return R.status(levelService.deleteLogic(Func.toLongList(ids)));
	}

	/**
	 * 导出数据
	 */
	@PreAuth(RoleConstant.HAS_ROLE_ADMIN)
	@GetMapping("/export-level")
	@ApiOperationSupport(order = 8)
	@Operation(summary = "导出数据", description  = "传入level")
	public void exportLevel(@Parameter(hidden = true) @RequestParam Map<String, Object> level, BladeUser bladeUser, HttpServletResponse response) {
		QueryWrapper<LevelEntity> queryWrapper = Condition.getQueryWrapper(level, LevelEntity.class);
		//if (!AuthUtil.isAdministrator()) {
		//	queryWrapper.lambda().eq(LevelEntity::getTenantId, bladeUser.getTenantId());
		//}
		//queryWrapper.lambda().eq(LevelEntity::getIsDeleted, BladeConstant.DB_NOT_DELETED);
		List<LevelExcel> list = levelService.exportLevel(queryWrapper);
		ExcelUtil.export(response, "数据" + DateUtil.time(), "数据表", list, LevelExcel.class);
	}

}
