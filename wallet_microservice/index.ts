import express from "express";
import type { Response, Request } from "express";
import chalk from "chalk";
import crypto from "crypto";

import { generateWallet, generateSecretKey } from "@stacks/wallet-sdk";
import { getAddressFromPrivateKey } from "@stacks/transactions";
import { STACKS_TESTNET } from "@stacks/network";
import {
	makeContractCall,
	AnchorMode,
	PostConditionMode,
	sponsorTransaction,
	broadcastTransaction,
	uintCV,
	standardPrincipalCV,
	noneCV,
	Pc,
	privateKeyToAddress,
} from "@stacks/transactions";

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
		stxPrivateKey: account?.stxPrivateKey,
	};
};

const sendSponsoredTx = async (
	usdcxAmount: number,
	recvAddr: string,
	senderAddress: string,
	senderPrivateKey: string,
	sponsorPrivateKey: string,
) => {
	const userTx = await makeContractCall({
		contractAddress: "ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM",
		contractName: "usdcx",
		functionName: "transfer",
		functionArgs: [
			uintCV(usdcxAmount * 1_000_000), // amount
			standardPrincipalCV(senderAddress), // sender (from)
			standardPrincipalCV(recvAddr), // recipient (to)
			noneCV(), // memo
		],
		sponsored: true, // ← critical flag
		fee: 0, // user pays nothing
		senderKey: senderPrivateKey,
		network: STACKS_TESTNET,
		postConditionMode: PostConditionMode.Deny,
		postConditions: [
			Pc.principal(senderAddress)
				.willSendEq(usdcxAmount * 1_000_000)
				.ft("ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM.usdcx", "usdcx-token"),
		],
	});

	const sponsoredTx = await sponsorTransaction({
		transaction: userTx,
		sponsorPrivateKey: sponsorPrivateKey,
		fee: 1000, // in microSTX — 1000 = 0.001 STX
		network: STACKS_TESTNET,
	});

	const result = await broadcastTransaction({
		transaction: sponsoredTx,
		network: STACKS_TESTNET,
	});

	return result;
};

const sendUSDCx = async (
	senderPrivateKey: string,
	recipientAddress: string,
	amount: number, // in micro units (6 decimals, so 1 USDCx = 1_000_000)
) => {
	const senderAddress = privateKeyToAddress(senderPrivateKey, STACKS_TESTNET);

	const txOptions = {
		contractAddress: "ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM",
		contractName: "usdcx",
		functionName: "transfer",
		functionArgs: [
			uintCV(amount * 1_000_000),
			standardPrincipalCV(senderAddress),
			standardPrincipalCV(recipientAddress),
			noneCV(), // memo
		],
		senderKey: senderPrivateKey,
		network: STACKS_TESTNET,
		anchorMode: AnchorMode.Any,
		postConditionMode: PostConditionMode.Deny,
		postConditions: [
			Pc.principal(senderAddress)
				.willSendEq(amount * 1_000_000)
				.ft("ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM.usdcx", "usdcx-token"),
		],
	};

	const tx = await makeContractCall(txOptions);
	const result = await broadcastTransaction({
		transaction: tx,
		network: STACKS_TESTNET,
	});

	console.log("TX Result:", result);
	return result;
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
		return next(error);
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
		return next(error);
	}

	if (!req.body.senderAddress) {
		const error = new Error("Err: Sponsor Private Key Not Found");
		return next(error);
	}

	if (!req.body.senderPrivateKey) {
		const error = new Error("Err: Sender Private Key Not Found");
		return next(error);
	}

	if (!req.body.sponsorPrivateKey) {
		const error = new Error("Err: Sponsor Private Key Not Found");
		return next(error);
	}

	const res_tx = await sendSponsoredTx(
		req.body.usdcxAmount,
		req.body.recvAddress,
		req.body.senderAddress,
		req.body.senderPrivateKey,
		req.body.sponsorPrivateKey,
	);

	console.log("RETURNED DATA:", res_tx);

	return res.send(res_tx);
});

app.post("/wallet/transfer", async (req: Request, res: Response, next: any) => {
	if (!req.body?.senderPrivateKey) {
		const error = new Error("Err: Sender Private Key Not Found");
		return next(error);
	}

	if (!req.body?.recipientAddress) {
		const error = new Error("Err: Recipient Address Not Found");
		return next(error);
	}

	if (!req.body?.usdcxAmount) {
		const error = new Error("Err: USDCx Amount Not Found");
		return next(error);
	}

	const transfer_tx = await sendUSDCx(
		req.body?.senderPrivateKey,
		req.body?.recipientAddress,
		req.body?.usdcxAmount,
	);

	return res.send(transfer_tx);
});

app.use(error);

app.listen(8080, () => {
	console.log(chalk.green("SERVER STARTED http://localhost:8080"));
});
