import express from "express";
import type { Response, Request } from "express";
import chalk from "chalk";

import crypto from "crypto";
import { generateWallet, generateSecretKey } from "@stacks/wallet-sdk";
import { getAddressFromPrivateKey } from "@stacks/transactions";
import { STACKS_TESTNET, STACKS_MAINNET } from "@stacks/network";

const app = express();

const createWallet = async () => {
	const secretKey = generateSecretKey();
	const password = crypto.randomBytes(32).toString("hex"); // unique per wallet

	const wallet = await generateWallet({ secretKey, password });
	const account = wallet.accounts[0];

	// derive address from private key
	const address = getAddressFromPrivateKey(
		account?.stxPrivateKey,
		STACKS_TESTNET, // swap to StacksMainnet() for production
	);

	console.log("genWallet", wallet, address);

	// store these securely (encrypted in DB)
	return {
		secretKey, // ← store encrypted
		password, // ← store encrypted
		address: address,
	};
};

app.get("/wallet/create", async (req: Request, res: Response) => {
	const wallet = await createWallet();
	console.log(wallet);

	res.send(wallet);
});

app.post("/wallet/restore", async (req: Request, res: Response) => {
	console.log(req.body);
});

app.listen(8000, () => {
	console.log(chalk.green("SERVER STARTED http://localhost:8000"));
});
