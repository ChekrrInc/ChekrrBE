import type { Request, Response } from "express";
import chalk from "chalk";

const logger = (req: Request, res: Response, next: any) => {
  if (req.method == "GET") {
    console.log(
      chalk.green(
        `${req.method} ${req?.protocol}://${req.get("host")}${req.originalUrl}`,
      ),
    );
  } else {
    console.log(
      chalk.yellow(
        `${req.method} ${req?.protocol}://${req.get("host")}${req.originalUrl}`,
      ),
    );
  }
  next();
};

export default logger;
