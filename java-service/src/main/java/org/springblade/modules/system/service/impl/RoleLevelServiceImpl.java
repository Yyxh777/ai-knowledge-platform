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
package org.springblade.modules.system.service.impl;

import org.springblade.modules.system.pojo.entity.RoleLevelEntity;
import org.springblade.modules.system.pojo.vo.RoleLevelVO;
import org.springblade.modules.system.excel.RoleLevelExcel;
import org.springblade.modules.system.mapper.RoleLevelMapper;
import org.springblade.modules.system.service.IRoleLevelService;
import org.springframework.stereotype.Service;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import org.springblade.core.mp.base.BaseServiceImpl;
import java.util.List;

/**
 *  服务实现类
 *
 * @author kj
 * @since 2026-02-28
 */
@Service
public class RoleLevelServiceImpl extends BaseServiceImpl<RoleLevelMapper, RoleLevelEntity> implements IRoleLevelService {

	@Override
	public IPage<RoleLevelVO> selectRoleLevelPage(IPage<RoleLevelVO> page, RoleLevelVO roleLevel) {
		return page.setRecords(baseMapper.selectRoleLevelPage(page, roleLevel));
	}

	@Override
	public List<RoleLevelExcel> exportRoleLevel(Wrapper<RoleLevelEntity> queryWrapper) {
		List<RoleLevelExcel> roleLevelList = baseMapper.exportRoleLevel(queryWrapper);
		//roleLevelList.forEach(roleLevel -> {
		//	roleLevel.setTypeName(DictCache.getValue(DictEnum.YES_NO, RoleLevelEntity.getType()));
		//});
		return roleLevelList;
	}

}
