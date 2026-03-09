import type { Request, Response } from "express";
import chalk from "chalk";

const error = (err: any, req: Request, res: Response, next: any) => {
  console.log(
    chalk.red(
      `ERR: ${req.method} ${req?.protocol}://${req.get("host")}${req.originalUrl}!!`,
    ),
  );

  res.json({ error: err.message });
};

export default error;
