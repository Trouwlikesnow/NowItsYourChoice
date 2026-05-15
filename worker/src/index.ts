import { downloadImage, replyMessage } from "./feishu";
import { recognizeTradeScreenshot } from "./llm";
import { normalizeBroker, fillFees } from "./fees";
import type { TradeRecord } from "./llm";
import type { FeeBreakdown } from "./fees";
import {
  createTradeRecord,
  findPortfolioPosition,
  updatePortfolioPosition,
  createPortfolioPosition,
} from "./bitable";

function parseTradeTime(raw: string): number {
  const todayMatch = raw.match(/今日\s*(\d{1,2}):(\d{2})(?::(\d{2}))?/);
  if (todayMatch) {
    const now = new Date();
    now.setHours(+todayMatch[1], +todayMatch[2], +(todayMatch[3] || 0), 0);
    return now.getTime();
  }
  const ts = new Date(raw).getTime();
  if (!isNaN(ts)) return ts;
  return Date.now();
}

async function updatePosition(
  env: Env,
  code: string,
  trade: TradeRecord,
  fees: FeeBreakdown,
  broker: string
): Promise<void> {
  const existing = await findPortfolioPosition(env, code, broker);

  if (existing) {
    const oldQty = Number(existing.fields["持仓数量"]) || 0;
    const oldCost = Number(existing.fields["成本金额"]) || 0;

    let newQty: number;
    let newCost: number;

    if (trade.direction === "买入") {
      newQty = oldQty + trade.quantity;
      newCost = oldCost + trade.amount + fees.total;
    } else {
      newQty = oldQty - trade.quantity;
      // Broker-style: sell reduces cost by sell amount, fees add to cost
      newCost = oldCost - trade.amount + fees.total;
    }

    if (newQty < 0) newQty = 0;
    if (newCost < 0) newCost = 0;
    const newCostPrice = newQty > 0 ? Math.round((newCost / newQty) * 10000) / 10000 : 0;

    await updatePortfolioPosition(env, existing.record_id, {
      持仓数量: newQty,
      成本价: newCostPrice,
      成本金额: Math.round(newCost * 100) / 100,
    });
  } else {
    // New position (only for buys)
    if (trade.direction !== "买入") return;
    const costAmount = Math.round((trade.amount + fees.total) * 100) / 100;
    const costPrice = Math.round((costAmount / trade.quantity) * 10000) / 10000;

    await createPortfolioPosition(env, {
      股票代码: trade.code || "",
      股票名称: trade.name || "",
      券商: broker,
      资金属性: "自有",
      持仓数量: trade.quantity,
      成本价: costPrice,
      成本金额: costAmount,
    });
  }
}

export interface Env {
  FEISHU_APP_ID: string;
  FEISHU_APP_SECRET: string;
  FEISHU_VERIFICATION_TOKEN: string;
  FEISHU_BASE_APP_TOKEN: string;
  TABLE_ID_TRADES: string;
  TABLE_ID_PORTFOLIO: string;
  LLM_API_BASE: string;
  LLM_API_KEY: string;
  LLM_MODEL: string;
}

interface FeishuEvent {
  challenge?: string;
  header?: { event_id?: string; event_type: string; token: string };
  event?: {
    message?: {
      message_id: string;
      message_type: string;
      content: string;
    };
  };
}

// Two-layer dedup: in-memory Set (instant, same isolate) + Cache API (cross-isolate)
const seenEvents = new Set<string>();

async function isDuplicate(eventId: string): Promise<boolean> {
  if (seenEvents.has(eventId)) return true;
  seenEvents.add(eventId);

  const cache = caches.default;
  const key = new Request(`https://dedup.internal/${eventId}`);
  const cached = await cache.match(key);
  if (cached) return true;
  await cache.put(key, new Response("1", {
    headers: { "Cache-Control": "max-age=300" },
  }));
  return false;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method !== "POST") {
      return new Response("OK", { status: 200 });
    }

    try {
      const body = (await request.json()) as FeishuEvent;

      // Challenge verification
      if (body.challenge) {
        return Response.json({ challenge: body.challenge });
      }

      // Verify token
      if (body.header?.token !== env.FEISHU_VERIFICATION_TOKEN) {
        return new Response("Unauthorized", { status: 401 });
      }

      const message = body.event?.message;
      if (!message) {
        return new Response("OK", { status: 200 });
      }

      // Deduplicate by event_id using Cache API (shared across isolates)
      const eventId = body.header?.event_id;
      if (eventId && (await isDuplicate(eventId))) {
        return new Response("OK", { status: 200 });
      }

      // Only handle image messages
      if (message.message_type !== "image") {
        await replyMessage(
          env,
          message.message_id,
          "请发送券商成交记录的截图，我来帮你识别录入。"
        );
        return new Response("OK", { status: 200 });
      }

      // Extract image_key from content JSON
      const content = JSON.parse(message.content) as { image_key: string };
      const imageKey = content.image_key;

      // Download image
      let imageBuffer: ArrayBuffer;
      try {
        imageBuffer = await downloadImage(env, message.message_id, imageKey);
      } catch (e) {
        await replyMessage(env, message.message_id, "❌ 图片获取失败，请重新发送");
        return new Response("OK", { status: 200 });
      }

      // Convert to base64
      const imageBase64 = btoa(
        String.fromCharCode(...new Uint8Array(imageBuffer))
      );

      // Call LLM
      let result;
      try {
        result = await recognizeTradeScreenshot(env, imageBase64);
        console.log("LLM result:", JSON.stringify(result));
      } catch (e) {
        const errMsg = e instanceof Error ? e.message : String(e);
        await replyMessage(env, message.message_id, `❌ 识别异常：${errMsg}`);
        return new Response("OK", { status: 200 });
      }

      if (result.error) {
        await replyMessage(
          env,
          message.message_id,
          `❌ 无法识别：${result.error}`
        );
        return new Response("OK", { status: 200 });
      }

      if (!result.trades || result.trades.length === 0) {
        await replyMessage(env, message.message_id, "❌ 未识别到任何交易记录");
        return new Response("OK", { status: 200 });
      }

      // Write to Bitable
      const hasCode = result.trades.some((t) => t.code);
      const broker = hasCode ? "华泰" : normalizeBroker(result.broker);
      const lines: string[] = [];

      for (let i = 0; i < result.trades.length; i++) {
        const trade = result.trades[i];
        const fees = fillFees(trade, broker);

        const fields: Record<string, unknown> = {
          股票代码: trade.code || "",
          股票名称: trade.name || "",
          方向: trade.direction,
          成交价: trade.price,
          成交数量: trade.quantity,
          成交金额: trade.amount,
          佣金: fees.commission,
          印花税: fees.stampTax,
          过户费: fees.transferFee,
          手续费合计: fees.total,
          券商: broker,
          来源: "截图识别",
          识别状态: "已确认",
        };

        if (trade.time) {
          fields["交易时间"] = parseTradeTime(trade.time);
        }

        try {
          await createTradeRecord(env, fields);
        } catch (e) {
          const errMsg = e instanceof Error ? e.message : String(e);
          console.error(`Failed to write trade ${i}:`, errMsg);
          await replyMessage(env, message.message_id, `❌ 写入失败：${errMsg}`);
          return new Response("OK", { status: 200 });
        }

        const feeStr = fees.total > 0 ? `  手续费 ${fees.total}` : "";
        const displayName =
          trade.name && trade.code
            ? `${trade.name}(${trade.code})`
            : trade.name || trade.code || "未知";
        lines.push(
          `${i + 1}. ${trade.direction} ${displayName} ` +
            `${trade.quantity}股 × ${trade.price} = ${trade.amount.toLocaleString()}${feeStr}`
        );
      }

      // Update portfolio positions
      const portfolioErrors: string[] = [];
      for (const trade of result.trades) {
        const fees = fillFees(trade, broker);
        const code = trade.code || trade.name || "";
        if (!code) continue;
        try {
          await updatePosition(env, code, trade, fees, broker);
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          console.error(`Portfolio update failed for ${code}:`, msg);
          portfolioErrors.push(code);
        }
      }

      const portfolioNote =
        portfolioErrors.length > 0
          ? `\n⚠️ 持仓更新失败：${portfolioErrors.join("、")}，将在每日同步时补充。`
          : "\n📊 持仓已同步更新。";

      const reply =
        `✅ 已录入 ${result.trades.length} 笔交易（${broker}）：\n\n` +
        lines.join("\n") +
        portfolioNote +
        "\n如有误差请在多维表格中修改。";

      await replyMessage(env, message.message_id, reply);
      return new Response("OK", { status: 200 });
    } catch (e) {
      console.error("Worker error:", e);
      return new Response("OK", { status: 200 });
    }
  },
};
