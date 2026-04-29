package org.springblade.test.sm2;

import lombok.SneakyThrows;
import org.bouncycastle.crypto.AsymmetricCipherKeyPair;
import org.bouncycastle.crypto.params.ECPrivateKeyParameters;
import org.bouncycastle.crypto.params.ECPublicKeyParameters;
import org.bouncycastle.util.encoders.Hex;
import org.springblade.core.tool.utils.SM2Util;

/**
 * SM2Test
 *
 * @author Chill
 */
public class Sm2Test {

	@SneakyThrows
	public static void main(String[] args) {
		AsymmetricCipherKeyPair keyPair = SM2Util.generateKeyPair();
		// ECPublicKeyParameters publicKey = (ECPublicKeyParameters) keyPair.getPublic();
		// ECPrivateKeyParameters privateKey = (ECPrivateKeyParameters) keyPair.getPrivate();

		String publicKeyString = SM2Util.getPublicKeyString(keyPair);
		String privateKeyString = SM2Util.getPrivateKeyString(keyPair);

		ECPublicKeyParameters publicKey = SM2Util.stringToPublicKey(publicKeyString);
		ECPrivateKeyParameters privateKey = SM2Util.stringToPrivateKey(privateKeyString);

		String originalText = "hello,bladex!";
		byte[] encryptedData = SM2Util.encrypt(originalText, publicKey);
		String decryptedText = SM2Util.decrypt(encryptedData, privateKey);

		byte[] signature = SM2Util.sign(originalText, privateKey);
		boolean isVerified = SM2Util.verify(originalText, signature, publicKey);

		System.out.println("===========================");
		System.out.println("Public Key: " + publicKeyString);
		System.out.println("Private Key: " + privateKeyString);

		System.out.println("Original: " + originalText);
		System.out.println("Encrypted: " + Hex.toHexString(encryptedData));
		System.out.println("Decrypted: " + decryptedText);
		System.out.println("Signature: " + Hex.toHexString(signature));
		System.out.println("Verified: " + isVerified);
		System.out.println("===========================");
	}

}
