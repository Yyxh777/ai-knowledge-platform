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

import org.springblade.modules.system.pojo.entity.LevelEntity;
import org.springblade.modules.system.pojo.vo.LevelVO;
import org.springblade.modules.system.excel.LevelExcel;
import org.springblade.modules.system.mapper.LevelMapper;
import org.springblade.modules.system.service.ILevelService;
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
public class LevelServiceImpl extends BaseServiceImpl<LevelMapper, LevelEntity> implements ILevelService {

	@Override
	public IPage<LevelVO> selectLevelPage(IPage<LevelVO> page, LevelVO level) {
		return page.setRecords(baseMapper.selectLevelPage(page, level));
	}

	@Override
	public List<LevelExcel> exportLevel(Wrapper<LevelEntity> queryWrapper) {
		List<LevelExcel> levelList = baseMapper.exportLevel(queryWrapper);
		//levelList.forEach(level -> {
		//	level.setTypeName(DictCache.getValue(DictEnum.YES_NO, LevelEntity.getType()));
		//});
		return levelList;
	}

}
