import type { TradeRecord } from "./llm";

const BROKER_COMMISSION: Record<string, number> = {
  招商: 0.00025,
  华泰: 0.0001,
};
const MIN_COMMISSION = 5;
const STAMP_TAX_RATE = 0.0005;
const TRANSFER_FEE_RATE = 0.00001;

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

export interface FeeBreakdown {
  commission: number;
  stampTax: number;
  transferFee: number;
  total: number;
}

export function estimateFees(
  amount: number,
  direction: string,
  broker: string
): FeeBreakdown {
  const rate = BROKER_COMMISSION[broker] ?? BROKER_COMMISSION["招商"];
  const commission = round2(Math.max(amount * rate, MIN_COMMISSION));
  const stampTax = direction === "卖出" ? round2(amount * STAMP_TAX_RATE) : 0;
  const transferFee = round2(amount * TRANSFER_FEE_RATE);
  return {
    commission,
    stampTax,
    transferFee,
    total: round2(commission + stampTax + transferFee),
  };
}

/** Normalize broker name from LLM output to our standard short names. */
export function normalizeBroker(raw: string | null): string {
  if (!raw) return "招商";
  if (raw.includes("华泰")) return "华泰";
  if (raw.includes("招商")) return "招商";
  return "招商"; // default
}

/** Fill in missing fee fields using estimation. */
export function fillFees(
  trade: TradeRecord,
  broker: string
): { commission: number; stampTax: number; transferFee: number; total: number } {
  const estimated = estimateFees(trade.amount, trade.direction, broker);
  return {
    commission: trade.commission ?? estimated.commission,
    stampTax: trade.stamp_tax ?? estimated.stampTax,
    transferFee: trade.transfer_fee ?? estimated.transferFee,
    total: round2(
      (trade.commission ?? estimated.commission) +
        (trade.stamp_tax ?? estimated.stampTax) +
        (trade.transfer_fee ?? estimated.transferFee)
    ),
  };
}
