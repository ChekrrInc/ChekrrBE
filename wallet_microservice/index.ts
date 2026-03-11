import express from "express";
import type { Response, Request } from "express";
import chalk from "chalk";
import crypto from "crypto";

import { generateWallet, generateSecretKey } from "@stacks/wallet-sdk";
import { getAddressFromPrivateKey } from "@stacks/transactions";
import { STACKS_TESTNET, STACKS_MAINNET } from "@stacks/network";

import logger from "./middleware/logger";
import error from "./middleware/error";

const app = express();

const getUSDCxBalance = async (address: string) => {
	const response = await fetch(
		`https://api.testnet.hiro.so/extended/v1/address/${address}/balances`,
	);
	const data: any = await response.json();
	const USDCX_CONTRACT =
		"ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM.usdcx::usdcx-token";

	const usdcxBal = (parseFloat(data.fungible_tokens[USDCX_CONTRACT].balance) /
		1_000_000) as number;

	return {
		walletAddress: address,
		walletBalance: usdcxBal,
	};
};

const createWallet = async () => {
	const secretKey = generateSecretKey();
	const password = crypto.randomBytes(32).toString("hex"); // unique per wallet

	const wallet = await generateWallet({ secretKey, password });
	const account = wallet.accounts[0];

	// derive address from private key
	const address = await getAddressFromPrivateKey(
		account?.stxPrivateKey as string,
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

app.use(logger);
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

app.get("/wallet/create", async (req: Request, res: Response) => {
	const wallet = await createWallet();
	res.status(201).send(wallet);
});

app.post("/wallet/restore", async (req: Request, res: Response, next: any) => {
	if (!req.body) {
		const error = new Error("Err: Invalid body [Body Not Found]");
		return next(error);
	}

	if (!req.body.secretKey) {
		const error = new Error("Err: Empty secret key Field");
		return next(error);
	}

	if (!req.body.password) {
		const error = new Error("Err: Empty password Field");
		return next(error);
	}

	let wallet = await generateWallet({
		secretKey: req.body.secretKey,
		password: req.body.password,
	});

	const account = wallet.accounts[0];
	const address = getAddressFromPrivateKey(
		account?.stxPrivateKey as string,
		STACKS_TESTNET,
	);

	res.send({ walletData: wallet, walletAddr: address });
});

app.post("/wallet/status", async (req: Request, res: Response, next: any) => {
	if (!req.body?.walletAddress) {
		const error = new Error("Err: Target Wallet Address Not Found");
		next(error);
	}
	const walletBalanceData = await getUSDCxBalance(req.body.walletAddress);
	res.send(walletBalanceData);
});

app.post("/wallet/send", async (req: Request, res: Response, next: any) => {
	if (!req.body?.recvAddress) {
		const error = new Error("Err: Recipient Wallet Address Not Found");
		next(error);
	}

	if (!req.body?.usdcxAmount) {
		const error = new Error("Err: USDCx amount not specified");
		next(error);
	}

	if (!req.body.senderPrivateKey) {
		const error = new Error("Err: Sender Private Key Not Found");
		next(error);
	}

	if (!req.body.masterWalletPrivateKey) {
		const error = new Error("Err: Sender Private Key Not Found");
		next(error);
	}
});

app.use(error);

app.listen(8000, () => {
	console.log(chalk.green("SERVER STARTED http://localhost:8000"));
});
