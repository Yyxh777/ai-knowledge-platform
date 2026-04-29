package org.springblade.test;

import org.bouncycastle.crypto.AsymmetricCipherKeyPair;
import org.bouncycastle.util.encoders.Hex;
import org.springblade.core.tool.utils.SM2Util;
import org.springblade.core.tool.utils.StringPool;

/**
 * 国密算法生成器
 *
 * @author Chill
 */
public class Sm2KeyGenerator {

	public static void main(String[] args) {
		System.out.println("================ blade.oauth2 配置如下 =================");
		AsymmetricCipherKeyPair keyPair = SM2Util.generateKeyPair();
//		String publicKey = SM2Util.getPublicKeyString(keyPair);
//		String privateKey = SM2Util.getPrivateKeyString(keyPair);
		String publicKey = "04023ab997ff3c39618e48ceff60a072d798eaa8322b953af7ab2de93c828cf7902ec9a4f7150c5e925d0fa07d8ddbb94a5ff7f682c809d9899ee5355b9699018f";
		String privateKey = "0ad27b0b20236277db14e18e234cc50808c3ad7320777fa55feb3fa13407cf8f";
		System.out.println("#blade配置 \n" +
			"blade:\n" +
			"  oauth2:\n" +
			"    enabled: true\n" +
			"    public-key: " + publicKey + "\n" +
			"    private-key: " + privateKey);
		System.out.println("=======================================================");
		System.out.println(StringPool.EMPTY);
		System.out.println("============== saber website.js 配置如下 ===============");
		System.out.println("//saber配置\n" +
			"oauth2: {\n" +
			"  publicKey: '" + publicKey + "',\n" +
			"}");
		System.out.println("=======================================================");
		System.out.println(StringPool.EMPTY);
		System.out.println("============== 密码:[admin] 加密流程如下 ================");
		String password = "admin";
		byte[] encryptedData = SM2Util.encrypt(password, publicKey);
		String decryptedText = SM2Util.decrypt(encryptedData, privateKey);
		System.out.println("加密前: " + password);
		System.out.println("加密后: " + Hex.toHexString(encryptedData));
		System.out.println("解密后: " + decryptedText);
		System.out.println("请注意: 此密文为前端加密后调用token接口的密码参数");
		System.out.println("=======================================================");
	}

}
