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
package org.springblade.common.filter;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springblade.core.log.exception.ServiceException;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * 演示过滤器
 *
 * @author Chill
 */
public class PreviewFilter implements Filter {

	private static final List<String> KEYS = new ArrayList<>();

	static {
		KEYS.add("notice");
		KEYS.add("process");
		KEYS.add("work");
		KEYS.add("token");
	}


	@Override
	public void init(FilterConfig filterConfig) {
	}


	@Override
	public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse, FilterChain filterChain) throws IOException, ServletException {

		HttpServletRequest httpServletRequest = (HttpServletRequest) servletRequest;
		String path = httpServletRequest.getServletPath();
		String method = httpServletRequest.getMethod();

		String get = "GET";
		if (method.equals(get) || KEYS.stream().anyMatch(path::contains)) {
			filterChain.doFilter(servletRequest, servletResponse);
		} else {
			throw new ServiceException("演示环境暂时无法操作！");
		}

	}

	@Override
	public void destroy() {
	}
}
